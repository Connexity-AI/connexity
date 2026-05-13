'use client';

import { useEnvironmentCard } from '../_hooks/use-environment-card';
import { DeleteEnvironmentDialog } from './delete-environment-dialog';
import { EnvironmentCardDeployFooter } from './environment-card-deploy-footer';
import { EnvironmentCardDestinationDetails } from './environment-card-destination-details';
import { EnvironmentCardHeader } from './environment-card-header';
import { EnvironmentCardPreviousDeployment } from './environment-card-previous-deployment';
import { EnvironmentCardSelectedVersion } from './environment-card-selected-version';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
  onEdit: (environment: EnvironmentPublic) => void;
}

export const EnvironmentCard: FC<Props> = ({ environment, agentId, onEdit }) => {
  const c = useEnvironmentCard({ environment, agentId });

  return (
    <>
      <div className="group border border-border rounded-lg overflow-hidden hover:border-primary/30 transition-colors flex flex-col">
        <EnvironmentCardHeader
          environment={environment}
          hasGate={c.hasGate}
          gateConfigDeleted={c.gateConfigDeleted}
          onEdit={onEdit}
          onDelete={() => c.setDeleteOpen(true)}
        />
        <EnvironmentCardDestinationDetails agentId={agentId} environment={environment} />
        <EnvironmentCardPreviousDeployment cardState={c} agentId={agentId} />
        <EnvironmentCardSelectedVersion cardState={c} agentId={agentId} />
        <EnvironmentCardDeployFooter cardState={c} />
      </div>

      <DeleteEnvironmentDialog
        open={c.deleteOpen}
        onOpenChange={c.setDeleteOpen}
        environment={environment}
        agentId={agentId}
      />
    </>
  );
};
