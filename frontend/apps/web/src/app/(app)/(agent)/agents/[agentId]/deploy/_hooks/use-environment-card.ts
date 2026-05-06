'use client';

import { useMemo, useState } from 'react';

import { CheckCircle2, FlaskConical, Loader2, Rocket } from 'lucide-react';

import { useAgentDeployments } from '@/app/(app)/(agent)/_hooks/use-agent-deployments';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { parseVersionName } from '@/app/(app)/(agent)/_utils/parse-version-name';
import { DeploymentStatus } from '@/client/types.gen';

import { useDeployWithFlash } from './use-deploy-with-flash';
import { useEvalGate } from './use-eval-gate';

import type { EnvironmentPublic } from '@/client/types.gen';

export interface PublishedVersion {
  version: number;
  title: string | null | undefined;
}

export interface ButtonState {
  label: string;
  Icon: typeof Rocket | null;
  disabled: boolean;
  spinning: boolean;
}

/**
 * Resolves the deploy button's user-facing state from a small set of
 * orthogonal flags. Pure / no React — kept separate so the precedence
 * order of the UI states is easy to read top-to-bottom.
 *
 * Precedence (highest first):
 *   1. Deploying           — mutation in flight, show spinner
 *   2. Deployed (flash)    — recently succeeded, show check for ~2s
 *   3. Running eval        — in-flight gated run we kicked off
 *   4. Waiting for eval    — gate state is pending/running for selection
 *   5. Run Evals and Deploy— gate exists but selection has no passing run
 *   6. Deploy              — default, ready to fire deploy
 */
function resolveButtonState(args: {
  baseDisabled: boolean;
  isDeploying: boolean;
  showSuccess: boolean;
  isInFlight: boolean;
  gateWaiting: boolean;
  showRunAndDeploy: boolean;
  gateConfigDeleted: boolean;
}): ButtonState {
  const {
    baseDisabled,
    isDeploying,
    showSuccess,
    isInFlight,
    gateWaiting,
    showRunAndDeploy,
    gateConfigDeleted,
  } = args;

  if (isDeploying) {
    return { label: 'Deploying…', Icon: Loader2, disabled: baseDisabled, spinning: true };
  }
  if (showSuccess) {
    return { label: 'Deployed', Icon: CheckCircle2, disabled: baseDisabled, spinning: false };
  }
  if (isInFlight) {
    return { label: 'Running eval…', Icon: Loader2, disabled: true, spinning: true };
  }
  if (gateWaiting) {
    return { label: 'Waiting for eval…', Icon: Loader2, disabled: true, spinning: false };
  }
  if (showRunAndDeploy) {
    return {
      label: 'Run Evals and Deploy',
      Icon: FlaskConical,
      // A deleted gate config means we can't kick off a run, so the
      // button has to be disabled even when we'd otherwise allow a click.
      disabled: baseDisabled || gateConfigDeleted,
      spinning: false,
    };
  }
  return { label: 'Deploy', Icon: Rocket, disabled: baseDisabled, spinning: false };
}

interface UseEnvironmentCardArgs {
  environment: EnvironmentPublic;
  agentId: string;
}

/**
 * Top-level hook for a single environment row on the deploy page.
 *
 * This hook is intentionally an *orchestrator*: it owns the small bits of
 * UI state that don't belong anywhere else (delete-dialog visibility,
 * the version chosen in the dropdown), pulls the data the card renders,
 * and delegates the two genuinely complex concerns to focused hooks:
 *
 *   - {@link useDeployWithFlash} — the deploy mutation plus the post-
 *     deploy "Deployed" success flash on the button.
 *   - {@link useEvalGate} — eval-gate detection, gate-run lookup, and the
 *     run-then-deploy flow that waits for an eval to pass before firing
 *     the actual deploy.
 *
 * The returned shape is the contract consumed by `EnvironmentCard`; keep
 * field names stable when refactoring.
 */
export function useEnvironmentCard({ environment, agentId }: UseEnvironmentCardArgs) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  // null until the user explicitly picks a version. We *derive* the
  // effective selection below by falling back to the latest published
  // version, so the dropdown always shows something useful without us
  // having to sync state in a useEffect.
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  const { data: versionsData, isLoading: versionsLoading } = useAgentVersions(agentId);
  const { data: deploymentsData } = useAgentDeployments(agentId);

  // Sorted descending: index 0 == newest. The dropdown renders this order
  // verbatim and the "(latest)" tag uses index 0.
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
  // Effective selection = explicit user choice, falling back to "latest".
  // Deriving rather than syncing into state avoids both an effect and the
  // brief mount window where `selectedVersion` would be null even though
  // we have a perfectly good default to show.
  const effectiveSelected = selectedVersion ?? latestPublished;
  const currentVersion = environment.current_version_number;

  // Latest *successful* deployment to this environment, regardless of
  // which version the user has currently selected. Drives the
  // "Previously Deployed" row of the card.
  const previousDeployment = useMemo(() => {
    const all = deploymentsData?.data ?? [];
    return (
      all
        .filter(
          (d) => d.environment_id === environment.id && d.status === DeploymentStatus.DEPLOYED
        )
        .sort((a, b) => b.deployed_at.localeCompare(a.deployed_at))[0] ?? null
    );
  }, [deploymentsData, environment.id]);

  const previousVersion = previousDeployment?.agent_version ?? null;
  const previousVersionTitle = useMemo(() => {
    if (previousVersion == null) return null;
    return publishedVersions.find((v) => v.version === previousVersion)?.title ?? null;
  }, [publishedVersions, previousVersion]);

  const deploy = useDeployWithFlash(agentId);

  // Gate logic lives in its own hook. We hand it the version we'd deploy
  // (so it can look up the relevant run) and a callback that fires the
  // deploy mutation once a fresh eval passes — at that point the gate has
  // done its job and the rest of the deploy is identical to the no-gate
  // path.
  const gate = useEvalGate({
    environment,
    agentId,
    selectedVersion: effectiveSelected,
    previousVersion,
    onEvalPassed: (version) => {
      deploy.mutate({ environmentId: environment.id, agentVersion: version });
    },
  });

  const sameAsCurrent = effectiveSelected === currentVersion;
  const noPublished = publishedVersions.length === 0;
  const baseDisabled =
    deploy.isPending || effectiveSelected == null || noPublished || sameAsCurrent;
  // Gate exists but selection isn't already passing -> we offer the
  // "Run Evals and Deploy" CTA instead of a direct deploy.
  const showRunAndDeploy =
    gate.hasGate && (gate.gateState === 'no-run' || gate.gateState === 'failed');
  // Gate exists and a run is in progress for the selection -> disable the
  // button entirely; the user just has to wait.
  const gateWaiting =
    gate.hasGate && (gate.gateState === 'pending' || gate.gateState === 'running');

  const button = resolveButtonState({
    baseDisabled,
    isDeploying: deploy.isPending,
    showSuccess: deploy.showSuccess,
    isInFlight: gate.isInFlight,
    gateWaiting,
    showRunAndDeploy,
    gateConfigDeleted: gate.gateConfigDeleted,
  });

  const selectDisabled =
    versionsLoading || publishedVersions.length === 0 || deploy.isPending || gate.isInFlight;

  // Combined error: deploy errors take priority over gate errors because
  // they're closer to the user's most recent action.
  const error = deploy.error || gate.error;

  const selectVersion = (value: string) => setSelectedVersion(Number(value));

  /**
   * Two-shape deploy handler:
   *   - If the env has a gate and the selection doesn't have a passing
   *     run yet, kick off a gated run via {@link useEvalGate}; the actual
   *     deploy will fire from `onEvalPassed` once the run passes.
   *   - Otherwise (no gate, or gate already passed) fire the deploy
   *     mutation immediately.
   */
  const handleDeploy = () => {
    if (effectiveSelected == null) return;

    if (showRunAndDeploy) {
      void gate.startGatedRun(effectiveSelected);
      return;
    }

    deploy.mutate({ environmentId: environment.id, agentVersion: effectiveSelected });
  };

  return {
    deleteOpen,
    setDeleteOpen,
    hasGate: gate.hasGate,
    gateConfigDeleted: gate.gateConfigDeleted,
    previousVersion,
    previousVersionTitle,
    previousDeployment,
    previousVersionRun: gate.previousVersionRun,
    currentVersion,
    latestPublished,
    publishedVersions,
    selectedVersion: effectiveSelected,
    selectVersion,
    selectDisabled,
    selectedVersionRun: gate.selectedVersionRun,
    button,
    handleDeploy,
    error,
  };
}
