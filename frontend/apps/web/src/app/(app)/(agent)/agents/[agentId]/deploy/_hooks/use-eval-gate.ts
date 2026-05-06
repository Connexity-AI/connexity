'use client';

import { useEffect, useMemo, useState } from 'react';

import { useQuery } from '@tanstack/react-query';

import { useCreateRun } from '@/app/(app)/(agent)/_hooks/use-create-run';
import { useRunStream } from '@/app/(app)/(agent)/_hooks/use-run-stream';
import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';
import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';
import { RunStatus } from '@/client/types.gen';

import type { EnvironmentPublic, RunPublic } from '@/client/types.gen';

/**
 * High-level gate state surfaced to the UI:
 *   - 'no-gate'  — environment has no eval gate configured
 *   - 'no-run'   — gated, but no run exists for the selected version yet
 *   - 'pending'  — a run exists, queued but not started
 *   - 'running'  — a run exists and is currently executing
 *   - 'passed'   — most recent run completed and met thresholds
 *   - 'failed'   — most recent run terminated without meeting thresholds
 */
export type GateState = 'no-gate' | 'pending' | 'running' | 'passed' | 'failed' | 'no-run';

/**
 * Picks the most recent run targeting a given (config, version) pair.
 * Newer runs supersede older ones, so we keep the maximum `created_at`.
 *
 * Returns undefined when the version is null, when no runs match, or when
 * the runs list simply hasn't loaded yet — callers branch on undefined to
 * mean "we don't have a run to show for this version".
 */
export function pickLatestRunForVersion(
  runs: RunPublic[],
  configId: string,
  version: number | null
): RunPublic | undefined {
  if (version == null) return undefined;
  let latest: RunPublic | undefined;
  for (const r of runs) {
    if (r.eval_config_id !== configId) continue;
    if (r.agent_version !== version) continue;
    if (!latest || r.created_at > latest.created_at) latest = r;
  }
  return latest;
}

interface UseEvalGateArgs {
  environment: EnvironmentPublic;
  agentId: string;
  /** Version the user currently has selected for deploy. */
  selectedVersion: number | null;
  /** Version that was last successfully deployed to this environment. */
  previousVersion: number | null;
  /**
   * Invoked once a run kicked off via {@link startGatedRun} terminates
   * successfully AND meets thresholds. Parent should treat this as the
   * "user implicitly clicked deploy" signal and fire the deploy mutation.
   */
  onEvalPassed: (version: number) => void;
}

/**
 * Owns the "eval gate" half of the deploy flow.
 *
 * An environment may declare an eval-config gate: a deploy is only allowed
 * once that config has been run against the candidate version and passed.
 * This hook concentrates all of the gate-related state and side effects so
 * the parent orchestrator (`useEnvironmentCard`) doesn't have to know how
 * any of it works.
 *
 * Responsibilities:
 *   1. Detect whether the environment is gated (`hasGate`) and whether its
 *      gate config still exists (`gateConfigDeleted` — a config row can
 *      be deleted while still referenced by an environment).
 *   2. Look up the latest run for both the previously-deployed version
 *      and the version the user currently has selected — these drive the
 *      "GatePills" UI on each row of the card.
 *   3. Derive `gateState`, the high-level enum the UI uses to choose
 *      button labels ("Run Evals and Deploy" vs "Waiting for eval…" etc).
 *   4. Provide `startGatedRun(version)` which kicks off a fresh run for
 *      `version`, subscribes to its stream, and fires `onEvalPassed` once
 *      it terminates successfully. Failures are surfaced via `error`.
 *
 * Note: gate-related queries are gated behind `enabled: hasGate` so that
 * ungated environments don't pay the cost of fetching configs and runs
 * just to render their deploy card.
 */
export function useEvalGate({
  environment,
  agentId,
  selectedVersion,
  previousVersion,
  onEvalPassed,
}: UseEvalGateArgs) {
  const gateConfigId = environment.eval_gate_eval_config_id ?? null;
  const hasGate = gateConfigId !== null;

  // Fetch the gate config row so we can detect "the config this env points
  // at has been deleted". Only enabled when there's a gate to look up.
  const { data: configsData } = useQuery({
    ...evalConfigsListQuery(agentId),
    enabled: hasGate,
  });

  const gateConfig = useMemo(
    () => (hasGate ? configsData?.data.find((c) => c.id === gateConfigId) : undefined),
    [hasGate, configsData, gateConfigId]
  );
  // Important: we only assert "deleted" once `configsData` has actually
  // loaded. While the query is in-flight, `gateConfig` is undefined too,
  // and we don't want to flash a "config deleted" badge during loading.
  const gateConfigDeleted = hasGate && configsData != null && gateConfig == null;

  // Full list of runs for this agent. We filter client-side because the
  // same list also drives `previousVersionRun` and the "any run for this
  // version" lookup, and refetching per-version would be wasteful.
  const { data: runsData } = useQuery({
    ...evalRunsListQuery(agentId),
    enabled: hasGate,
  });
  const allRuns = useMemo<RunPublic[]>(() => runsData?.data ?? [], [runsData]);

  const previousVersionRun = useMemo(
    () =>
      hasGate && gateConfigId
        ? pickLatestRunForVersion(allRuns, gateConfigId, previousVersion)
        : undefined,
    [hasGate, gateConfigId, allRuns, previousVersion]
  );
  const selectedVersionRun = useMemo(
    () =>
      hasGate && gateConfigId
        ? pickLatestRunForVersion(allRuns, gateConfigId, selectedVersion)
        : undefined,
    [hasGate, gateConfigId, allRuns, selectedVersion]
  );

  // In-flight "run-then-deploy" tracking. When the user clicks "Run Evals
  // and Deploy", we kick off a new run, store its id here, and the watcher
  // effect below waits for it to terminate. Cleared once we've handled the
  // terminal state (success or failure).
  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const [pendingDeployVersion, setPendingDeployVersion] = useState<number | null>(null);
  const [gateError, setGateError] = useState<string | null>(null);

  const createRun = useCreateRun(agentId);

  // Streams server-sent events for the in-flight run into the runs query
  // cache. The watcher effect below reads from that cache, so we don't
  // need to do anything with the stream's return value directly — we
  // just need it running while we have a pending run.
  useRunStream({
    runId: pendingRunId ?? '',
    agentId,
    enabled: pendingRunId !== null,
  });

  // Watch the runs cache for our pending run reaching a terminal state.
  //   - PENDING / RUNNING        -> keep waiting
  //   - COMPLETED + thresholds   -> notify parent (it fires the deploy)
  //   - COMPLETED + failed       -> set a gate error
  //   - any other terminal state -> set a gate error
  // In every terminal branch we clear the pending state so we don't
  // re-fire on subsequent renders.
  useEffect(() => {
    if (!pendingRunId || pendingDeployVersion == null) return;
    const run = allRuns.find((r) => r.id === pendingRunId);
    if (!run) return;
    if (run.status === RunStatus.PENDING || run.status === RunStatus.RUNNING) return;

    if (run.status === RunStatus.COMPLETED) {
      const m = run.aggregate_metrics;
      if (m?.metrics_passed && m?.cases_passed) {
        onEvalPassed(pendingDeployVersion);
      } else {
        setGateError('Eval failed: thresholds not met. Adjust the agent and try again.');
      }
    } else {
      setGateError(`Eval ${run.status}. Try again.`);
    }
    setPendingRunId(null);
    setPendingDeployVersion(null);
  }, [allRuns, onEvalPassed, pendingDeployVersion, pendingRunId]);

  const gateState: GateState = useMemo(() => {
    if (!hasGate) return 'no-gate';
    const run = selectedVersionRun;
    if (!run) return 'no-run';
    if (run.status === RunStatus.PENDING) return 'pending';
    if (run.status === RunStatus.RUNNING) return 'running';
    if (run.status === RunStatus.COMPLETED) {
      const m = run.aggregate_metrics;
      if (m?.metrics_passed && m?.cases_passed) return 'passed';
    }
    // COMPLETED-but-failed, ERROR, CANCELLED, etc all collapse to 'failed'
    // for the UI's purposes; the user just needs to see "try again".
    return 'failed';
  }, [hasGate, selectedVersionRun]);

  /**
   * Kicks off a fresh eval run for `version` and arms the watcher above.
   *
   * Resolves once the run has been *created* on the server, NOT when it
   * completes — the eventual pass/fail outcome is delivered asynchronously
   * via `onEvalPassed` (success) or by setting `error` (failure).
   *
   * Safe to no-op when there's no gate configured; callers don't need to
   * branch on `hasGate` themselves.
   */
  const startGatedRun = async (version: number) => {
    if (!gateConfigId) return;
    setGateError(null);
    try {
      const created = await createRun.mutateAsync({
        body: {
          agent_id: agentId,
          eval_config_id: gateConfigId,
          agent_version: version,
        },
        autoExecute: true,
      });
      setPendingRunId(created.id);
      setPendingDeployVersion(version);
    } catch (err) {
      setGateError(err instanceof Error ? err.message : 'Failed to start eval run');
    }
  };

  return {
    hasGate,
    gateConfigDeleted,
    previousVersionRun,
    selectedVersionRun,
    gateState,
    /** True while a gated run kicked off here is still in flight. */
    isInFlight: pendingRunId !== null,
    /** Either the gate-specific error or whatever createRun surfaced. */
    error: gateError ?? createRun.error,
    startGatedRun,
  };
}
