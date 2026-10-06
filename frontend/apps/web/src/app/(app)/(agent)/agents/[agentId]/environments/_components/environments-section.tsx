'use client';

import { useState } from 'react';

import { Plus, Zap } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';
import { AddEnvironmentDialog } from './add-environment-dialog';
import { EnvironmentsList } from './environments-list';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  agentId: string;
}

export const EnvironmentsSection: FC<Props> = ({ agentId }) => {
  const [addOpen, setAddOpen] = useState(false);
  const [editingEnvironment, setEditingEnvironment] = useState<EnvironmentPublic | null>(null);
  const { data } = useEnvironments(agentId);
  const environments = data?.data ?? [];

  const openAddDialog = () => {
    setEditingEnvironment(null);
    setAddOpen(true);
  };

  const openEditDialog = (environment: EnvironmentPublic) => {
    setEditingEnvironment(environment);
    setAddOpen(true);
  };

  return (
    <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-xs text-muted-foreground uppercase tracking-wider">Environments</h2>
          </div>

          <Button
            variant="ghost"
            className="h-auto px-2 py-1 gap-1.5 text-xs font-normal text-muted-foreground hover:text-foreground hover:bg-transparent [&_svg]:size-3.5"
            onClick={openAddDialog}
          >
            <Plus />
            Add environment
          </Button>
        </div>

        <EnvironmentsList
          environments={environments}
          agentId={agentId}
          onAdd={openAddDialog}
          onEdit={openEditDialog}
        />

        <AddEnvironmentDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          environment={editingEnvironment}
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
