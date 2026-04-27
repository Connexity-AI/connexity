'use client';

import { useState } from 'react';

import { Plus, Rocket, Zap } from 'lucide-react';

import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';

import { AddEnvironmentDialog } from './add-environment-dialog';
import { EnvironmentCard } from './environment-card';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  agentId: string;
  integrations: IntegrationPublic[];
}

export const EnvironmentsSection: FC<Props> = ({ agentId, integrations }) => {
  const [addOpen, setAddOpen] = useState(false);
  const { data } = useEnvironments(agentId);
  const environments = data?.data ?? [];

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-xs text-muted-foreground uppercase tracking-wider">Environments</h2>
        </div>
        <button
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          onClick={() => setAddOpen(true)}
        >
          <Plus className="w-3.5 h-3.5" />
          Add environment
        </button>
      </div>

      {environments.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border flex flex-col items-center justify-center py-12 gap-3">
          <Rocket className="w-8 h-8 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">No environments yet</p>
          <button
            className="flex items-center gap-1.5 text-xs text-foreground hover:underline cursor-pointer"
            onClick={() => setAddOpen(true)}
          >
            <Plus className="w-3.5 h-3.5" />
            Add your first environment
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {environments.map((env) => (
            <EnvironmentCard key={env.id} environment={env} agentId={agentId} />
          ))}
        </div>
      )}

      <AddEnvironmentDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        agentId={agentId}
        integrations={integrations}
      />
    </section>
  );
};

export function EnvironmentsSectionSkeleton() {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded bg-muted animate-pulse" />
          <div className="h-3 w-24 rounded bg-muted animate-pulse" />
        </div>
        <div className="h-4 w-28 rounded bg-muted animate-pulse" />
      </div>
      <div className="rounded-xl border border-dashed border-border h-40 animate-pulse bg-muted/30" />
    </section>
  );
}
