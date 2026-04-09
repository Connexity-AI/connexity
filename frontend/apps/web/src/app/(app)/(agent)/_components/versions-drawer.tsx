'use client';

import { History, RotateCcw, X } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@workspace/ui/components/ui/drawer';
import { Button } from '@workspace/ui/components/ui/button';

import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { useAgentDraft } from '@/app/(app)/(agent)/_hooks/use-agent-draft';
import { useRollbackAgent } from '@/app/(app)/(agent)/_hooks/use-rollback-agent';
import { formatTimeAgo } from '@/app/(app)/(agent)/_utils/format-time-ago';

import type { AgentVersionPublic } from '@/client/types.gen';

function parseVersionName(changeDescription: string | null): {
  name: string | null;
  description: string | null;
} {
  if (!changeDescription) return { name: null, description: null };
  const lines = changeDescription.split('\n');
  if (lines.length <= 1) return { name: lines[0] || null, description: null };
  return { name: lines[0] || null, description: lines.slice(1).join('\n').trim() || null };
}

export function VersionsDrawer() {
  const { isDrawerOpen, closeDrawer, selectedVersion, selectVersion } = useVersions();
  const { agentId } = useAgentEditFormActions();
  const { data: versionsData } = useAgentVersions(agentId);
  const { data: draft } = useAgentDraft(agentId, true);
  const { mutate: rollback, isPending: isRollingBack } = useRollbackAgent(agentId);

  const versions = versionsData?.data ?? [];
  const sorted = [...versions].sort((a, b) => (b.version ?? 0) - (a.version ?? 0));

  const handleRollback = (version: AgentVersionPublic) => {
    const { name } = parseVersionName(version.change_description);
    rollback(
      {
        version: version.version!,
        change_description: `Rollback to V${version.version}${name ? ` — ${name}` : ''}`,
      },
      {
        onSuccess: () => {
          selectVersion(null);
        },
      }
    );
  };

  return (
    <Drawer direction="right" open={isDrawerOpen} onOpenChange={(open: boolean) => !open && closeDrawer()}>
      <DrawerContent>
        <DrawerHeader className="flex flex-row items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <DrawerTitle className="text-sm font-medium">Versions</DrawerTitle>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={closeDrawer}>
            <X className="h-4 w-4" />
          </Button>
        </DrawerHeader>

        <div className="flex-1 overflow-auto py-2">
          {/* Draft row */}
          {draft && (
            <div className="px-2 pb-2">
              <button
                onClick={() => selectVersion(null)}
                className={cn(
                  'w-full text-left px-3 py-3 rounded-md transition-colors',
                  selectedVersion === null ? 'bg-accent' : 'hover:bg-accent/50'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground">Draft</span>
                    <span className="text-[10px] bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 px-1.5 py-0.5 rounded">
                      latest
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatTimeAgo(draft.created_at)}
                  </span>
                </div>
              </button>
              <div className="mt-2 border-t border-border" />
            </div>
          )}

          {/* Published versions */}
          <div className="px-2 space-y-1">
            {sorted.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-6 px-3">
                No published versions yet. Click Publish to create one.
              </p>
            )}
            {sorted.map((v) => {
              const isSelected = selectedVersion === v.version;
              const isLatestPublished = v.version === sorted[0]?.version;
              const { name, description } = parseVersionName(v.change_description);

              return (
                <div key={v.id} className="group relative">
                  <button
                    onClick={() => selectVersion(v.version!)}
                    className={cn(
                      'w-full text-left px-3 py-3 rounded-md transition-colors',
                      isSelected ? 'bg-accent' : 'hover:bg-accent/50'
                    )}
                  >
                    <div className="flex items-center justify-between mb-1 gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs font-medium text-foreground shrink-0">
                          V{v.version}
                          {name ? ` — ${name}` : ''}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatTimeAgo(v.created_at)}
                      </span>
                    </div>

                    {description && (
                      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                        {description}
                      </p>
                    )}
                  </button>

                  {/* Rollback button on hover for non-latest versions */}
                  {!isLatestPublished && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRollback(v);
                      }}
                      disabled={isRollingBack}
                      className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 bg-background"
                    >
                      <RotateCcw className="w-2.5 h-2.5" />
                      Rollback
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
