'use client';

import { useEffect, useMemo, useState } from 'react';

import { AlertCircle, CheckCircle2, Loader2, Rocket, Trash2 } from 'lucide-react';

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
import { parseVersionName } from '@/app/(app)/(agent)/_utils/parse-version-name';

import { DeleteEnvironmentDialog } from './delete-environment-dialog';

import { Platform, type EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
}

interface PublishedVersion {
  version: number;
  title: string | null | undefined;
}

const SUCCESS_FLASH_MS = 2000;

export const EnvironmentCard: FC<Props> = ({ environment, agentId }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const { data: versionsData, isLoading: versionsLoading } = useAgentVersions(agentId);
  const deploy = useDeployEnvironment(agentId);

  const publishedVersions: PublishedVersion[] = useMemo(() => {
    const rows = versionsData?.data ?? [];
    return rows
      .filter((v): v is typeof v & { version: number } => v.version != null)
      .map((v) => ({
        version: v.version,
        title: parseVersionName(v.change_description).name,
      }))
      .sort((a, b) => b.version - a.version);
  }, [versionsData]);

  const latestPublished = publishedVersions[0]?.version ?? null;
  const currentVersion = environment.current_version_number;

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
              {PLATFORM_LABELS[environment.platform]}
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
            <p className="text-sm text-foreground tabular-nums">—</p>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm text-foreground font-medium">
                  v{currentVersion}
                </span>
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
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {publishedVersions.map((v) => (
                  <SelectItem key={v.version} value={String(v.version)} className="text-xs">
                    v{v.version}
                    {v.title ? ` — ${v.title}` : ''}
                    {v.version === latestPublished ? ' (latest)' : ''}
                    {v.version === currentVersion ? ' · current' : ''}
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
