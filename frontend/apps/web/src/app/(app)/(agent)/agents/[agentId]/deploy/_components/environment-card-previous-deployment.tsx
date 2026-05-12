import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';
import { GatePills } from './gate-pills';

import type { useEnvironmentCard } from '../_hooks/use-environment-card';
import type { FC } from 'react';

type EnvironmentCardState = ReturnType<typeof useEnvironmentCard>;

interface Props {
  cardState: EnvironmentCardState;
  agentId: string;
}

interface PreviousVersionLabelProps {
  version: number;
  title: string | null;
}

const PreviousVersionLabel: FC<PreviousVersionLabelProps> = ({ version, title }) => {
  if (!title) {
    return <p className="text-sm text-foreground tabular-nums">v{version}</p>;
  }

  return (
    <p className="text-sm text-foreground tabular-nums">
      v{version}
      <span className="text-muted-foreground font-normal"> — {title}</span>
    </p>
  );
};

interface PreviousVersionDateProps {
  deployedAt: string;
}

const PreviousVersionDate: FC<PreviousVersionDateProps> = ({ deployedAt }) => {
  return (
    <p className="text-[10px] text-muted-foreground mt-1">Deployed: {formatTimeAgo(deployedAt)}</p>
  );
};

const PreviousVersionContent: FC<Props> = ({ cardState }) => {
  if (cardState.previousVersion == null) {
    return <p className="text-sm text-foreground tabular-nums">—</p>;
  }

  const deployedAt = cardState.previousDeployment?.deployed_at;

  if (!deployedAt) {
    return (
      <PreviousVersionLabel version={cardState.previousVersion} title={cardState.previousVersionTitle} />
    );
  }

  return (
    <>
      <PreviousVersionLabel version={cardState.previousVersion} title={cardState.previousVersionTitle} />
      <PreviousVersionDate deployedAt={deployedAt} />
    </>
  );
};

const PreviousVersionGatePills: FC<Props> = ({ cardState, agentId }) => {
  if (!cardState.hasGate) {
    return null;
  }
  if (cardState.previousVersion == null) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 shrink-0">
      <GatePills run={cardState.previousVersionRun} agentId={agentId} />
    </div>
  );
};

export const EnvironmentCardPreviousDeployment: FC<Props> = ({ cardState, agentId }) => {
  return (
    <div className="px-5 py-3 border-b border-border">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
            Previously Deployed
          </p>
          <PreviousVersionContent cardState={cardState} agentId={agentId} />
        </div>
        <PreviousVersionGatePills cardState={cardState} agentId={agentId} />
      </div>
    </div>
  );
};
