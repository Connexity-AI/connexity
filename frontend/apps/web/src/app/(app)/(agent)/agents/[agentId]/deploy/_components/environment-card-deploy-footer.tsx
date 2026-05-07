import { AlertCircle } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import type { useEnvironmentCard } from '../_hooks/use-environment-card';
import type { FC } from 'react';

type EnvironmentCardState = ReturnType<typeof useEnvironmentCard>;

interface Props {
  cardState: EnvironmentCardState;
}

function getFooterLayoutClass(error: string | null): string {
  if (error) {
    return 'justify-between';
  }
  return 'justify-end';
}

const DeployError: FC<{ error: string | null }> = ({ error }) => {
  if (!error) {
    return null;
  }

  return (
    <div className="flex items-start gap-1.5 text-xs text-red-400 min-w-0">
      <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
      <span className="truncate">{error}</span>
    </div>
  );
};

const DeployButtonIcon: FC<{
  cardState: EnvironmentCardState;
}> = ({ cardState }) => {
  const Icon = cardState.button.Icon;
  if (!Icon) {
    return null;
  }

  let className = 'w-3.5 h-3.5 mr-1.5';
  if (cardState.button.spinning) {
    className = `${className} animate-spin`;
  }

  return <Icon className={className} />;
};

export const EnvironmentCardDeployFooter: FC<Props> = ({ cardState }) => {
  const layoutClass = getFooterLayoutClass(cardState.error);

  return (
    <div className={`px-5 py-4 flex items-center gap-3 mt-auto ${layoutClass}`}>
      <DeployError error={cardState.error} />
      <Button
        type="button"
        size="sm"
        onClick={cardState.handleDeploy}
        disabled={cardState.button.disabled}
        className="h-9 text-xs shrink-0"
      >
        <DeployButtonIcon cardState={cardState} />
        {cardState.button.label}
      </Button>
    </div>
  );
};
