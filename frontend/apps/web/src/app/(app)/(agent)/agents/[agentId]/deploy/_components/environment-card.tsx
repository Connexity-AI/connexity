'use client';

import { useEffect, useMemo, useState } from 'react';

import { AlertCircle, CheckCircle2, History, Loader2, Rocket, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { useDeployEnvironment } from '@/app/(app)/(agent)/_hooks/use-deploy-environment';
import { useEnvironmentDeployments } from '@/app/(app)/(agent)/_hooks/use-environment-deployments';

import { DeleteEnvironmentDialog } from './delete-environment-dialog';

import type { DeploymentPublic, EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
}

const SUCCESS_FLASH_MS = 2000;

export const EnvironmentCard: FC<Props> = ({ environment, agentId }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const { data: versionsData, isLoading: versionsLoading } = useAgentVersions(agentId);
  const deploy = useDeployEnvironment(agentId);

  const publishedVersions = useMemo(() => {
    const rows = versionsData?.data ?? [];
    return rows
      .filter((v) => v.status === 'published' && v.version != null)
      .map((v) => v.version as number)
      .sort((a, b) => b - a);
  }, [versionsData]);

  const latestPublished = publishedVersions[0] ?? null;
  const currentVersion = environment.current_version_number;

  useEffect(() => {
    if (selectedVersion != null) return;
    if (latestPublished == null) return;
    setSelectedVersion(latestPublished);
  }, [latestPublished, selectedVersion]);

  useEffect(() => {
    if (!deploy.isSuccess) return;
    setShowSuccess(true);
    const t = setTimeout(() => {
      setShowSuccess(false);
      deploy.reset();
    }, SUCCESS_FLASH_MS);
    return () => clearTimeout(t);
  }, [deploy.isSuccess, deploy]);

  const handleDeploy = () => {
    if (selectedVersion == null) return;
    deploy.mutate({ environmentId: environment.id, agentVersion: selectedVersion });
  };

  const deployDisabled =
    deploy.isPending ||
    selectedVersion == null ||
    publishedVersions.length === 0 ||
    selectedVersion === currentVersion;

  let buttonLabel = 'Deploy';
  let ButtonIcon: typeof Rocket | null = Rocket;
  if (deploy.isPending) {
    buttonLabel = 'Deploying…';
    ButtonIcon = Loader2;
  } else if (showSuccess) {
    buttonLabel = 'Deployed';
    ButtonIcon = CheckCircle2;
  }

  return (
    <>
      <div className="group border border-border rounded-lg overflow-hidden hover:border-primary/30 transition-colors">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)] shrink-0" />
            <span className="text-sm text-foreground">{environment.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">
              Retell
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              className="text-muted-foreground/40 hover:text-red-400 transition-colors cursor-pointer"
              title="Remove environment"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Integration
            </span>
            <span className="text-xs text-foreground">{environment.integration_name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Retell Agent
            </span>
            <span className="text-xs text-foreground">
              {environment.platform_agent_name || environment.platform_agent_id}
            </span>
          </div>
        </div>

        <div className="px-5 py-4 border-b border-border space-y-2">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
            Current Version
          </div>
          {currentVersion == null ? (
            <div className="text-xs text-muted-foreground/70 italic">
              Not deployed yet
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm text-foreground font-medium">
                  v{currentVersion}
                </span>
                {environment.current_version_name && (
                  <span className="text-xs text-muted-foreground">
                    · {environment.current_version_name}
                  </span>
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {formatTimeAgo(environment.current_deployed_at)}
              </span>
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-b border-border space-y-3">
          <div className="flex items-center gap-2">
            <Select
              value={selectedVersion != null ? String(selectedVersion) : ''}
              onValueChange={(v) => setSelectedVersion(Number(v))}
              disabled={versionsLoading || publishedVersions.length === 0 || deploy.isPending}
            >
              <SelectTrigger className="h-9 text-xs flex-1">
                <SelectValue
                  placeholder={
                    versionsLoading
                      ? 'Loading versions…'
                      : publishedVersions.length === 0
                        ? 'No published versions'
                        : 'Select version'
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {publishedVersions.map((v) => (
                  <SelectItem key={v} value={String(v)} className="text-xs">
                    v{v}
                    {v === latestPublished ? ' (latest)' : ''}
                    {v === currentVersion ? ' · current' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              type="button"
              size="sm"
              onClick={handleDeploy}
              disabled={deployDisabled}
              className="h-9 text-xs"
            >
              {ButtonIcon && (
                <ButtonIcon
                  className={`w-3.5 h-3.5 mr-1.5 ${deploy.isPending ? 'animate-spin' : ''}`}
                />
              )}
              {buttonLabel}
            </Button>
          </div>

          {deploy.error && (
            <div className="flex items-start gap-1.5 text-xs text-red-400">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{deploy.error}</span>
            </div>
          )}
        </div>

        <div className="px-5 py-3">
          <button
            className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors cursor-pointer"
            onClick={() => setHistoryOpen((o) => !o)}
          >
            <History className="w-3.5 h-3.5" />
            Deployment history
            <span className="text-muted-foreground/60 normal-case tracking-normal">
              {historyOpen ? '(hide)' : '(show)'}
            </span>
          </button>
          {historyOpen && (
            <div className="mt-3">
              <DeploymentHistoryTable environmentId={environment.id} />
            </div>
          )}
        </div>
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

const DeploymentHistoryTable: FC<{ environmentId: string }> = ({ environmentId }) => {
  const { data, isLoading, isError } = useEnvironmentDeployments(environmentId);

  if (isLoading) {
    return <div className="text-xs text-muted-foreground">Loading history…</div>;
  }
  if (isError) {
    return <div className="text-xs text-red-400">Failed to load history</div>;
  }
  const rows = data?.data ?? [];
  if (rows.length === 0) {
    return <div className="text-xs text-muted-foreground italic">No deployments yet</div>;
  }

  return (
    <div className="border border-border rounded-md overflow-hidden">
      <table className="w-full text-xs">
        <thead className="bg-accent/10">
          <tr className="text-left text-[10px] text-muted-foreground uppercase tracking-wider">
            <th className="px-3 py-2 font-normal">Environment</th>
            <th className="px-3 py-2 font-normal">Version</th>
            <th className="px-3 py-2 font-normal">By</th>
            <th className="px-3 py-2 font-normal">When</th>
            <th className="px-3 py-2 font-normal">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <DeploymentHistoryRow key={d.id} deployment={d} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

const DeploymentHistoryRow: FC<{ deployment: DeploymentPublic }> = ({ deployment }) => {
  const isFailed = deployment.status === 'failed';
  const isPending = deployment.status === 'pending';
  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2 text-foreground">{deployment.environment_name}</td>
      <td className="px-3 py-2 text-foreground">
        v{deployment.agent_version}
        {deployment.retell_version_name && (
          <span className="text-muted-foreground"> · {deployment.retell_version_name}</span>
        )}
      </td>
      <td className="px-3 py-2 text-muted-foreground">{deployment.deployed_by_name ?? '—'}</td>
      <td className="px-3 py-2 text-muted-foreground">{formatTimeAgo(deployment.deployed_at)}</td>
      <td className="px-3 py-2">
        <span
          className={
            isFailed
              ? 'text-red-400'
              : isPending
                ? 'text-amber-400'
                : 'text-green-400'
          }
          title={isFailed && deployment.error_message ? deployment.error_message : undefined}
        >
          {deployment.status}
        </span>
      </td>
    </tr>
  );
};
