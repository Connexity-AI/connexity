'use client';

import { useState } from 'react';

import { Activity, AlertCircle, CheckCheck, Loader2, Plus, Zap } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';
import { useAgentDeployments } from '@/app/(app)/(agent)/_hooks/use-agent-deployments';
import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';
import { AddEnvironmentDialog } from './add-environment-dialog';
import { EnvironmentsList } from './environments-list';

import type { DeploymentPublic, EnvironmentPublic } from '@/client/types.gen';
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
    <>
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

      <DeploymentHistorySection agentId={agentId} />
    </>
  );
};

const DeploymentHistorySection: FC<{ agentId: string }> = ({ agentId }) => {
  const { data, isLoading, isError } = useAgentDeployments(agentId);
  const rows = data?.data ?? [];

  const header = (
    <div className="flex items-center gap-2 mb-4">
      <Activity className="w-4 h-4 text-muted-foreground" />
      <h2 className="text-xs text-muted-foreground uppercase tracking-wider">Deployment history</h2>
    </div>
  );

  if (isLoading) {
    return (
      <section>
        {header}
        <div className="text-xs text-muted-foreground">Loading history…</div>
      </section>
    );
  }

  if (isError) {
    return (
      <section>
        {header}
        <div className="text-xs text-red-400">Failed to load history</div>
      </section>
    );
  }

  if (rows.length === 0) {
    return (
      <section>
        {header}
        <div className="text-xs text-muted-foreground italic">No deployments yet</div>
      </section>
    );
  }

  return (
    <section>
      {header}
      <div className="rounded-xl border border-border bg-background overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider font-normal">
                Environment
              </th>
              <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider font-normal">
                Version
              </th>
              <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider font-normal">
                By
              </th>
              <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider font-normal">
                When
              </th>
              <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider font-normal">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <DeploymentHistoryRow key={d.id} deployment={d} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

const DeploymentHistoryRow: FC<{ deployment: DeploymentPublic }> = ({ deployment }) => {
  const isFailed = deployment.status === 'failed';
  const isPending = deployment.status === 'pending';
  return (
    <tr className="border-b border-border last:border-0 hover:bg-accent/20 transition-colors">
      <td className="px-5 py-3 text-foreground">{deployment.environment_name}</td>
      <td className="px-5 py-3 text-foreground tabular-nums">
        v{deployment.agent_version}
        {deployment.retell_version_name && (
          <span className="text-muted-foreground"> · {deployment.retell_version_name}</span>
        )}
      </td>
      <td className="px-5 py-3 text-muted-foreground">{deployment.deployed_by_display_name ?? '—'}</td>
      <td className="px-5 py-3 text-muted-foreground">{formatTimeAgo(deployment.deployed_at)}</td>
      <td className="px-5 py-3">
        {isFailed ? (
          <span
            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400"
            title={deployment.error_message ?? undefined}
          >
            <AlertCircle className="w-2.5 h-2.5" />
            Failed
          </span>
        ) : isPending ? (
          <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">
            <Loader2 className="w-2.5 h-2.5 animate-spin" />
            Pending
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">
            <CheckCheck className="w-2.5 h-2.5" />
            Success
          </span>
        )}
      </td>
    </tr>
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
