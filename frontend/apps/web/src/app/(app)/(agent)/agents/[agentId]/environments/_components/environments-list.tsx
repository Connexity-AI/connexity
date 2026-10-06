'use client';

import { Plus, Rocket } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { EnvironmentCard } from './environment-card';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environments: EnvironmentPublic[];
  agentId: string;
  onAdd: () => void;
  onEdit: (environment: EnvironmentPublic) => void;
}

export const EnvironmentsList: FC<Props> = ({ environments, agentId, onAdd, onEdit }) => {
  if (environments.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border flex flex-col items-center justify-center py-12 gap-3">
        <Rocket className="w-8 h-8 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">No environments yet</p>
        <Button
          variant="link"
          className="h-auto p-0 gap-1.5 text-xs font-normal text-foreground [&_svg]:size-3.5"
          onClick={onAdd}
        >
          <Plus />
          Add your first environment
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {environments.map((env) => (
        <EnvironmentCard key={env.id} environment={env} agentId={agentId} onEdit={onEdit} />
      ))}
    </div>
  );
};
