'use client';

import { useState } from 'react';

import { Trash2 } from 'lucide-react';

import { DeleteEnvironmentDialog } from './delete-environment-dialog';

import { Platform, type EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  agentId: string;
}

const PLATFORM_LABELS: Record<Platform, string> = {
  [Platform.RETELL]: 'Retell',
};

export const EnvironmentCard: FC<Props> = ({ environment, agentId }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);

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
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-foreground">{environment.integration_name}</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Retell Agent</span>
            </div>
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-xs text-foreground">
                {environment.platform_agent_name || environment.platform_agent_id}
              </span>
            </div>
          </div>
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
