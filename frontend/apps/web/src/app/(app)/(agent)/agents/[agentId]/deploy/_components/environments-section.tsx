'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';

import { Plus, Zap } from 'lucide-react';

import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';
import { AddEnvironmentDialog } from './add-environment-dialog';
import { EnvironmentsList } from './environments-list';

export const EnvironmentsSection = () => {
  const [addOpen, setAddOpen] = useState(false);
  const { agentId } = useParams<{ agentId: string }>();
  const { data } = useEnvironments(agentId);
  const environments = data.data;

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

      <EnvironmentsList
        environments={environments}
        agentId={agentId}
        onAdd={() => setAddOpen(true)}
      />

      <AddEnvironmentDialog open={addOpen} onOpenChange={setAddOpen} />
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
