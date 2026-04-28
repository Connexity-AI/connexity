'use client';

import { Plus, Rocket } from 'lucide-react';

import { EnvironmentCard } from './environment-card';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environments: EnvironmentPublic[];
  agentId: string;
  onAdd: () => void;
}

export const EnvironmentsList: FC<Props> = ({ environments, agentId, onAdd }) => {
  if (environments.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border flex flex-col items-center justify-center py-12 gap-3">
        <Rocket className="w-8 h-8 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">No environments yet</p>
        <button
          className="flex items-center gap-1.5 text-xs text-foreground hover:underline cursor-pointer"
          onClick={onAdd}
        >
          <Plus className="w-3.5 h-3.5" />
          Add your first environment
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {environments.map((env) => (
        <EnvironmentCard key={env.id} environment={env} agentId={agentId} />
      ))}
    </div>
  );
};
