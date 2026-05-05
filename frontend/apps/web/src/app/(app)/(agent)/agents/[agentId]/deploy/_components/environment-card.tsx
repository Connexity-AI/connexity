'use client';

import { useEffect, useMemo, useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  CircleCheck,
  CircleX,
  FlaskConical,
  ListChecks,
  Loader2,
  Rocket,
  ShieldCheck,
  Target,
  Trash2,
} from 'lucide-react';
import Link from 'next/link';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { useCreateRun } from '@/app/(app)/(agent)/_hooks/use-create-run';
import { useDeployEnvironment } from '@/app/(app)/(agent)/_hooks/use-deploy-environment';
import { useRunStream } from '@/app/(app)/(agent)/_hooks/use-run-stream';
import { roundScore } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/score-utils';
import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';
import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';
import { parseVersionName } from '@/app/(app)/(agent)/_utils/parse-version-name';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { RunStatus } from '@/client/types.gen';

import { DeleteEnvironmentDialog } from './delete-environment-dialog';

import type { EnvironmentPublic, RunPublic } from '@/client/types.gen';
import type { FC } from 'react';

import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
}

interface PublishedVersion {
  version: number;
  title: string | null | undefined;
}

const SUCCESS_FLASH_MS = 2000;

const PILL =
  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono tabular-nums';
const PILL_PASS = 'bg-green-500/10 text-green-400 border-green-500/20';
const PILL_FAIL = 'bg-red-500/10 text-red-400 border-red-500/20';

function pickLatestRunForVersion(
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

function GatePills({ run, agentId }: { run: RunPublic | undefined; agentId: string }) {
  if (!run) {
    return <span className="text-[10px] text-muted-foreground/50">No run yet</span>;
  }
  if (run.status === RunStatus.PENDING || run.status === RunStatus.RUNNING) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="w-3 h-3 rounded-full border-2 border-violet-400/40 border-t-violet-400 animate-spin shrink-0" />
        <span className="text-[10px] text-violet-400">Running…</span>
      </div>
    );
  }

  const m = run.aggregate_metrics;
  const score = roundScore(m?.weighted_metrics_score_pct);
  const metricsPassed = m?.metrics_passed ?? null;
  const casesPassed = m?.cases_passed ?? null;
  const passedCount = m?.passed_count ?? 0;
  const totalExecutions = m?.total_executions ?? 0;
  const overallPassed = metricsPassed === true && casesPassed === true;

  return (
    <div className="flex items-center gap-1.5">
      {score !== null && metricsPassed !== null ? (
        <span
          className={cn(PILL, metricsPassed ? PILL_PASS : PILL_FAIL)}
          title="Metrics score"
        >
          <Target className="w-2.5 h-2.5" />
          Metrics {score}%
        </span>
      ) : null}
      {casesPassed !== null && totalExecutions > 0 ? (
        <span
          className={cn(PILL, casesPassed ? PILL_PASS : PILL_FAIL)}
          title="Test cases"
        >
          <ListChecks className="w-2.5 h-2.5" />
          Test Cases {passedCount}/{totalExecutions}
        </span>
      ) : null}
      {metricsPassed !== null && casesPassed !== null ? (
        overallPassed ? (
          <CircleCheck className="w-3.5 h-3.5 text-green-400 shrink-0" />
        ) : (
          <CircleX className="w-3.5 h-3.5 text-red-400 shrink-0" />
        )
      ) : null}
      <Link
        href={UrlGenerator.agentEvalsRuns(agentId)}
        className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors ml-1"
      >
        View
      </Link>
    </div>
  );
}

export const EnvironmentCard: FC<Props> = ({ environment, agentId }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const [pendingDeployVersion, setPendingDeployVersion] = useState<number | null>(null);
  const [gateError, setGateError] = useState<string | null>(null);

  const { data: versionsData, isLoading: versionsLoading } = useAgentVersions(agentId);
  const deploy = useDeployEnvironment(agentId);
  const createRun = useCreateRun(agentId);

  const gateConfigId = environment.eval_gate_eval_config_id ?? null;
  const hasGate = gateConfigId !== null;

  const { data: configsData } = useQuery({
    ...evalConfigsListQuery(agentId),
    enabled: hasGate,
  });
  const gateConfig = useMemo(
    () =>
      hasGate ? configsData?.data.find((c) => c.id === gateConfigId) : undefined,
    [hasGate, configsData, gateConfigId]
  );
  const gateConfigDeleted = hasGate && configsData != null && gateConfig == null;

  const { data: runsData } = useQuery({
    ...evalRunsListQuery(agentId),
    enabled: hasGate,
  });
  const allRuns = useMemo<RunPublic[]>(() => runsData?.data ?? [], [runsData]);

  const publishedVersions: PublishedVersion[] = useMemo(() => {
    const rows = versionsData?.data ?? [];
    return rows
      .filter((v): v is typeof v & { version: number } => v.version != null)
      .map((v) => ({
        version: v.version,
        title: parseVersionName(v.change_description).name,
      }))
      .sort((a, b) => b.version - a.version);
  }, [versionsData]);

  const latestPublished = publishedVersions[0]?.version ?? null;
  const currentVersion = environment.current_version_number;

  const currentVersionRun = useMemo(
    () =>
      hasGate && gateConfigId
        ? pickLatestRunForVersion(allRuns, gateConfigId, currentVersion)
        : undefined,
    [hasGate, gateConfigId, allRuns, currentVersion]
  );
  const selectedVersionRun = useMemo(
    () =>
      hasGate && gateConfigId
        ? pickLatestRunForVersion(allRuns, gateConfigId, selectedVersion)
        : undefined,
    [hasGate, gateConfigId, allRuns, selectedVersion]
  );

  useRunStream({
    runId: pendingRunId ?? '',
    agentId,
    enabled: pendingRunId !== null,
  });

  useEffect(() => {
    if (!pendingRunId || pendingDeployVersion == null) return;
    const run = allRuns.find((r) => r.id === pendingRunId);
    if (!run) return;
    if (run.status === RunStatus.PENDING || run.status === RunStatus.RUNNING) {
      return;
    }
    if (run.status === RunStatus.COMPLETED) {
      const m = run.aggregate_metrics;
      if (m?.metrics_passed && m?.cases_passed) {
        deploy.mutate({
          environmentId: environment.id,
          agentVersion: pendingDeployVersion,
        });
      } else {
        setGateError('Eval failed: thresholds not met. Adjust the agent and try again.');
      }
    } else {
      setGateError(`Eval ${run.status}. Try again.`);
    }
    setPendingRunId(null);
    setPendingDeployVersion(null);
  }, [allRuns, deploy, environment.id, pendingDeployVersion, pendingRunId]);

  useEffect(() => {
    if (!deploy.isSuccess) return;
    setShowSuccess(true);
    const t = setTimeout(() => {
      setShowSuccess(false);
      deploy.reset();
    }, SUCCESS_FLASH_MS);
    return () => clearTimeout(t);
  }, [deploy.isSuccess, deploy]);

  useEffect(() => {
    if (selectedVersion != null) return;
    if (latestPublished == null) return;
    setSelectedVersion(latestPublished);
  }, [latestPublished, selectedVersion]);

  const gateState: 'no-gate' | 'pending' | 'running' | 'passed' | 'failed' | 'no-run' = (() => {
    if (!hasGate) return 'no-gate';
    const run = selectedVersionRun;
    if (!run) return 'no-run';
    if (run.status === RunStatus.PENDING) return 'pending';
    if (run.status === RunStatus.RUNNING) return 'running';
    if (run.status === RunStatus.COMPLETED) {
      const m = run.aggregate_metrics;
      if (m?.metrics_passed && m?.cases_passed) return 'passed';
    }
    return 'failed';
  })();

  const isInFlight = pendingRunId !== null;
  const sameAsCurrent = selectedVersion === currentVersion;
  const noPublished = publishedVersions.length === 0;
  const baseDisabled =
    deploy.isPending || selectedVersion == null || noPublished || sameAsCurrent;

  const showRunAndDeploy =
    hasGate && (gateState === 'no-run' || gateState === 'failed');

  let buttonLabel = 'Deploy';
  let ButtonIcon: typeof Rocket | null = Rocket;
  let buttonDisabled = baseDisabled;

  if (deploy.isPending) {
    buttonLabel = 'Deploying…';
    ButtonIcon = Loader2;
  } else if (showSuccess) {
    buttonLabel = 'Deployed';
    ButtonIcon = CheckCircle2;
  } else if (isInFlight) {
    buttonLabel = 'Running eval…';
    ButtonIcon = Loader2;
    buttonDisabled = true;
  } else if (hasGate && (gateState === 'pending' || gateState === 'running')) {
    buttonLabel = 'Waiting for eval…';
    ButtonIcon = Loader2;
    buttonDisabled = true;
  } else if (showRunAndDeploy) {
    buttonLabel = 'Run Evals and Deploy';
    ButtonIcon = FlaskConical;
    buttonDisabled = baseDisabled || gateConfigDeleted;
  }

  const handleDeploy = async () => {
    if (selectedVersion == null) return;
    setGateError(null);

    if (showRunAndDeploy && gateConfigId) {
      try {
        const created = await createRun.mutateAsync({
          body: { agent_id: agentId, eval_config_id: gateConfigId },
          autoExecute: true,
        });
        setPendingRunId(created.id);
        setPendingDeployVersion(selectedVersion);
      } catch (err) {
        setGateError(err instanceof Error ? err.message : 'Failed to start eval run');
      }
      return;
    }

    deploy.mutate({ environmentId: environment.id, agentVersion: selectedVersion });
  };

  return (
    <>
      <div className="group border border-border rounded-lg overflow-hidden hover:border-primary/30 transition-colors flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)] shrink-0" />
            <span className="text-sm text-foreground">{environment.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">
              Retell
            </span>
            {hasGate && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 inline-flex items-center gap-1">
                <ShieldCheck className="w-2.5 h-2.5" />
                Eval gate
              </span>
            )}
            {gateConfigDeleted && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                config deleted
              </span>
            )}
          </div>
          <button
            className="text-muted-foreground/40 hover:text-red-400 transition-colors cursor-pointer"
            title="Remove environment"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Integration / Retell Agent */}
        <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Integration
            </span>
            <span className="text-xs text-foreground">{environment.integration_name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Retell Agent
            </span>
            <span className="text-xs text-foreground">
              {environment.platform_agent_name || environment.platform_agent_id}
            </span>
          </div>
        </div>

        {/* Current Version */}
        <div className="px-5 py-3 border-b border-border">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                Current Version
              </p>
              {currentVersion == null ? (
                <p className="text-sm text-foreground tabular-nums">—</p>
              ) : (
                <>
                  <p className="text-sm text-foreground tabular-nums">
                    v{currentVersion}
                    {environment.current_version_name ? (
                      <span className="text-muted-foreground font-normal">
                        {' '}
                        — {environment.current_version_name}
                      </span>
                    ) : null}
                  </p>
                  {environment.current_deployed_at && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Deployed: {formatTimeAgo(environment.current_deployed_at)}
                    </p>
                  )}
                </>
              )}
            </div>
            {hasGate && currentVersion != null && (
              <div className="flex items-center gap-2 shrink-0">
                <GatePills run={currentVersionRun} agentId={agentId} />
              </div>
            )}
          </div>
        </div>

        {/* Selected Version */}
        <div className="px-5 py-3 border-b border-border">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">
                Selected Version
              </p>
              <Select
                value={selectedVersion != null ? String(selectedVersion) : ''}
                onValueChange={(v) => setSelectedVersion(Number(v))}
                disabled={
                  versionsLoading ||
                  publishedVersions.length === 0 ||
                  deploy.isPending ||
                  isInFlight
                }
              >
                <SelectTrigger className="h-8 text-xs max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {publishedVersions.map((v) => (
                    <SelectItem key={v.version} value={String(v.version)} className="text-xs">
                      v{v.version}
                      {v.title ? ` — ${v.title}` : ''}
                      {v.version === latestPublished ? ' (latest)' : ''}
                      {v.version === currentVersion ? ' · current' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {hasGate && (
              <div className="flex items-center gap-2 shrink-0">
                <GatePills run={selectedVersionRun} agentId={agentId} />
              </div>
            )}
          </div>
        </div>

        {/* Deploy button */}
        <div className="px-5 py-4 flex items-center justify-end mt-auto">
          <Button
            type="button"
            size="sm"
            onClick={handleDeploy}
            disabled={buttonDisabled}
            className="h-9 text-xs"
          >
            {ButtonIcon && (
              <ButtonIcon
                className={`w-3.5 h-3.5 mr-1.5 ${
                  deploy.isPending || isInFlight ? 'animate-spin' : ''
                }`}
              />
            )}
            {buttonLabel}
          </Button>
        </div>

        {/* Errors */}
        {(deploy.error || gateError || createRun.error) && (
          <div className="px-5 pb-4 -mt-2 flex items-start gap-1.5 text-xs text-red-400">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{deploy.error || gateError || createRun.error}</span>
          </div>
        )}
      </div>

      <DeleteEnvironmentDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        environment={environment}
        agentId={agentId}
      />
    </>
  );
};
