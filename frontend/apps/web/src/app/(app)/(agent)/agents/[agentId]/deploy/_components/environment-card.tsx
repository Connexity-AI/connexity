'use client';

import { useState } from 'react';

import { DeleteEnvironmentDialog } from './delete-environment-dialog';
import { EnvironmentCardDestinationDetails } from './environment-card-destination-details';
import { EnvironmentCardHeader } from './environment-card-header';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
  onEdit: (environment: EnvironmentPublic) => void;
}

export const EnvironmentCard: FC<Props> = ({ environment, agentId, onEdit }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <div className="group border border-border rounded-lg overflow-hidden hover:border-primary/30 transition-colors flex flex-col">
        <EnvironmentCardHeader
          environment={environment}
          onEdit={onEdit}
          onDelete={() => setDeleteOpen(true)}
        />
        <EnvironmentCardDestinationDetails agentId={agentId} environment={environment} />
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
