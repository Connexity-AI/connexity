'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';

import { Activity, AlertCircle, CheckCheck, Loader2, Plus, Rocket, Zap } from 'lucide-react';

import { useAgentDeployments } from '@/app/(app)/(agent)/_hooks/use-agent-deployments';
import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';
import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';

import { AddEnvironmentDialog } from './add-environment-dialog';
import { EnvironmentCard } from './environment-card';

import type { DeploymentPublic, IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  agentId: string;
  integrations: IntegrationPublic[];
}

export const EnvironmentsSection = () => {
  const [addOpen, setAddOpen] = useState(false);
  const { agentId } = useParams<{ agentId: string }>();
  const { data } = useEnvironments(agentId);
  const environments = data.data;

  return (
    <>
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

      <DeploymentHistorySection agentId={agentId} />
    </>
  );
};

const DeploymentHistorySection: FC<{ agentId: string }> = ({ agentId }) => {
  const { data, isLoading, isError } = useAgentDeployments(agentId);
  const rows = data?.data ?? [];

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-muted-foreground" />
        <h2 className="text-xs text-muted-foreground uppercase tracking-wider">
          Deployment history
        </h2>
      </div>

      {isLoading ? (
        <div className="text-xs text-muted-foreground">Loading history…</div>
      ) : isError ? (
        <div className="text-xs text-red-400">Failed to load history</div>
      ) : rows.length === 0 ? (
        <div className="text-xs text-muted-foreground italic">No deployments yet</div>
      ) : (
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
      )}
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
      <td className="px-5 py-3 text-muted-foreground">{deployment.deployed_by_name ?? '—'}</td>
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
