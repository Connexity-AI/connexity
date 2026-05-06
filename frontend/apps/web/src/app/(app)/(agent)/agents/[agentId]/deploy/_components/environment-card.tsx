'use client';

import { AlertCircle, ShieldCheck, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';
import { useEnvironmentCard } from '../_hooks/use-environment-card';
import { DeleteEnvironmentDialog } from './delete-environment-dialog';
import { GatePills } from './gate-pills';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
}

export const EnvironmentCard: FC<Props> = ({ environment, agentId }) => {
  const c = useEnvironmentCard({ environment, agentId });
  const { Icon } = c.button;

  return (
    <>
      <div className="group border border-border rounded-lg overflow-hidden hover:border-primary/30 transition-colors flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)] shrink-0" />
            <span className="text-sm text-foreground">{environment.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">
              Retell
            </span>
            {c.hasGate && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 inline-flex items-center gap-1">
                <ShieldCheck className="w-2.5 h-2.5" />
                Eval gate
              </span>
            )}
            {c.gateConfigDeleted && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                config deleted
              </span>
            )}
          </div>
          <button
            className="text-muted-foreground/40 hover:text-red-400 transition-colors cursor-pointer"
            title="Remove environment"
            onClick={() => c.setDeleteOpen(true)}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Integration / Retell Agent */}
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

        {/* Previously Deployed */}
        <div className="px-5 py-3 border-b border-border">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                Previously Deployed
              </p>
              {c.previousVersion == null ? (
                <p className="text-sm text-foreground tabular-nums">—</p>
              ) : (
                <>
                  <p className="text-sm text-foreground tabular-nums">
                    v{c.previousVersion}
                    {c.previousVersionTitle && (
                      <span className="text-muted-foreground font-normal">
                        {' '}
                        — {c.previousVersionTitle}
                      </span>
                    )}
                  </p>
                  {c.previousDeployment?.deployed_at && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Deployed: {formatTimeAgo(c.previousDeployment.deployed_at)}
                    </p>
                  )}
                </>
              )}
            </div>
            {c.hasGate && c.previousVersion != null && (
              <div className="flex items-center gap-2 shrink-0">
                <GatePills run={c.previousVersionRun} agentId={agentId} />
              </div>
            )}
          </div>
        </div>

        {/* Selected Version */}
        <div className="px-5 py-3 border-b border-border">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">
                Selected Version
              </p>
              <Select
                value={c.selectedVersion != null ? String(c.selectedVersion) : ''}
                onValueChange={c.selectVersion}
                disabled={c.selectDisabled}
              >
                <SelectTrigger className="h-8 text-xs max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {c.publishedVersions.map((v) => (
                    <SelectItem key={v.version} value={String(v.version)} className="text-xs">
                      v{v.version}
                      {v.title ? ` — ${v.title}` : ''}
                      {v.version === c.latestPublished ? ' (latest)' : ''}
                      {v.version === c.currentVersion ? ' · current' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {c.hasGate && (
              <div className="flex items-center gap-2 shrink-0">
                <GatePills run={c.selectedVersionRun} agentId={agentId} />
              </div>
            )}
          </div>
        </div>

        {/* Deploy button (with inline error) */}
        <div
          className={`px-5 py-4 flex items-center gap-3 mt-auto ${
            c.error ? 'justify-between' : 'justify-end'
          }`}
        >
          {c.error && (
            <div className="flex items-start gap-1.5 text-xs text-red-400 min-w-0">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span className="truncate">{c.error}</span>
            </div>
          )}
          <Button
            type="button"
            size="sm"
            onClick={c.handleDeploy}
            disabled={c.button.disabled}
            className="h-9 text-xs shrink-0"
          >
            {Icon && (
              <Icon
                className={`w-3.5 h-3.5 mr-1.5 ${c.button.spinning ? 'animate-spin' : ''}`}
              />
            )}
            {c.button.label}
          </Button>
        </div>
      </div>

      <DeleteEnvironmentDialog
        open={c.deleteOpen}
        onOpenChange={c.setDeleteOpen}
        environment={environment}
        agentId={agentId}
      />
    </>
  );
};
