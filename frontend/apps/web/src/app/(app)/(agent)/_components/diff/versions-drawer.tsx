'use client';

import { History, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@workspace/ui/components/ui/drawer';
import { cn } from '@workspace/ui/lib/utils';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentDraft } from '@/app/(app)/(agent)/_hooks/use-agent-draft';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { formatTimeAgo } from '@/app/(app)/(agent)/_utils/format-time-ago';

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
  const versions = versionsData?.data ?? [];
  const sorted = [...versions].sort((a, b) => (b.version ?? 0) - (a.version ?? 0));

  return (
    <Drawer
      direction="right"
      modal={false}
      open={isDrawerOpen}
      onOpenChange={(open: boolean) => !open && closeDrawer()}
    >
      <DrawerContent onInteractOutside={closeDrawer}>
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
              <Button
                variant="ghost"
                onClick={() => selectVersion(null)}
                className={cn(
                  'w-full h-auto block text-left px-3 py-3 rounded-md whitespace-normal transition-colors',
                  selectedVersion === null ? 'bg-accent' : 'hover:bg-accent/50'
                )}
              >
                <div className="flex items-center justify-between">
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
              </Button>
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

            {sorted.map((version) => {
              const isSelected = selectedVersion === version.version;
              const { name, description } = parseVersionName(version.change_description);

              return (
                <div key={version.id}>
                  <Button
                    variant="ghost"
                    onClick={() => selectVersion(version.version!)}
                    className={cn(
                      'w-full h-auto block text-left px-3 py-3 rounded-md whitespace-normal transition-colors',
                      isSelected ? 'bg-accent' : 'hover:bg-accent/50'
                    )}
                  >
                    <div
                      className={cn(
                        'flex items-center justify-between gap-2',
                        description && 'mb-1'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-xs font-medium text-foreground truncate">
                          Version {version.version}
                          {name ? ` — ${name}` : ''}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatTimeAgo(version.created_at)}
                      </span>
                    </div>

                    {description && (
                      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                        {description}
                      </p>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
