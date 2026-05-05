'use client';

import { useMemo } from 'react';

import { useQuery } from '@tanstack/react-query';
import { History, Rocket, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@workspace/ui/components/ui/drawer';
import { cn } from '@workspace/ui/lib/utils';

import { roundScore } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/score-utils';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentDraft } from '@/app/(app)/(agent)/_hooks/use-agent-draft';
import { useAgentDeployments } from '@/app/(app)/(agent)/_hooks/use-agent-deployments';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';
import { formatTimeAgo } from '@/app/(app)/(agent)/_utils/format-time-ago';
import { parseVersionName } from '@/app/(app)/(agent)/_utils/parse-version-name';

import type { RunPublic } from '@/client/types.gen';

function parseUtcDate(iso: string): Date {
  const utcStr = iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`;
  return new Date(utcStr);
}

function runDateIso(run: RunPublic): string {
  return run.completed_at ?? run.started_at ?? run.created_at;
}

function formatShortDate(iso: string): string {
  return parseUtcDate(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function pickLatestCompletedByVersion(runs: RunPublic[]): Map<number, RunPublic> {
  const out = new Map<number, RunPublic>();
  for (const run of runs) {
    if (run.status !== 'completed') continue;
    if (run.agent_version === null || run.agent_version === undefined) continue;
    const existing = out.get(run.agent_version);
    if (
      !existing ||
      parseUtcDate(runDateIso(run)).getTime() >
        parseUtcDate(runDateIso(existing)).getTime()
    ) {
      out.set(run.agent_version, run);
    }
  }
  return out;
}

export function VersionsDrawer() {
  const { isDrawerOpen, closeDrawer, selectedVersion, selectVersion } = useVersions();
  const { agentId } = useAgentEditFormActions();
  const { data: versionsData } = useAgentVersions(agentId);
  const { data: deploymentsData } = useAgentDeployments(agentId);
  const { data: draft } = useAgentDraft(agentId, true);
  const { data: runsData } = useQuery(evalRunsListQuery(agentId));
  const versions = versionsData?.data ?? [];
  const sorted = [...versions].sort((a, b) => (b.version ?? 0) - (a.version ?? 0));

  const deployedAtByVersion = new Map<number, string>();
  for (const d of deploymentsData?.data ?? []) {
    if (d.status !== 'deployed') continue;
    const existing = deployedAtByVersion.get(d.agent_version);
    if (
      !existing ||
      parseUtcDate(d.deployed_at).getTime() > parseUtcDate(existing).getTime()
    ) {
      deployedAtByVersion.set(d.agent_version, d.deployed_at);
    }
  }

  const latestRunByVersion = useMemo(
    () => pickLatestCompletedByVersion(runsData?.data ?? []),
    [runsData]
  );

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
              const deployedAt =
                version.version != null
                  ? deployedAtByVersion.get(version.version)
                  : undefined;
              const isDeployed = Boolean(deployedAt);
              const latestRun =
                version.version != null ? latestRunByVersion.get(version.version) : undefined;
              const metrics = latestRun?.aggregate_metrics ?? null;
              const score = roundScore(metrics?.avg_overall_score);
              const totalExecutions = metrics?.total_executions ?? 0;
              const passedCount = metrics?.passed_count ?? 0;
              const allPassed = totalExecutions > 0 && passedCount === totalExecutions;

              return (
                <div key={version.id}>
                  <Button
                    variant="ghost"
                    onClick={() => selectVersion(version.version!)}
                    className={cn(
                      'w-full h-auto block text-left px-3 py-3 rounded-md whitespace-normal transition-colors',
                      isSelected ? 'bg-accent' : 'hover:bg-accent/50',
                      isDeployed && !isSelected && 'ring-1 ring-inset ring-green-500/30'
                    )}
                  >
                    <div
                      className={cn(
                        'flex items-center justify-between gap-2',
                        (description || isDeployed) && 'mb-1'
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-xs font-medium text-foreground truncate">
                          Version {version.version}
                          {name ? ` — ${name}` : ''}
                        </span>
                        {isDeployed && (
                          <span className="inline-flex items-center gap-1 text-[10px] bg-green-500/15 text-green-600 dark:text-green-400 px-1.5 py-0.5 rounded shrink-0">
                            <Rocket className="w-2.5 h-2.5" />
                            Deployed
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatTimeAgo(deployedAt ?? version.created_at)}
                      </span>
                    </div>

                    {isDeployed && deployedAt && (
                      <p className="text-[10px] text-green-600/80 dark:text-green-400/70 mb-1.5">
                        Deployed {formatShortDate(deployedAt)}
                      </p>
                    )}

                    {description && (
                      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                        {description}
                      </p>
                    )}

                    {latestRun && (
                      <div className="mt-2.5 rounded border border-border overflow-hidden">
                        <div className="flex items-center justify-between px-2.5 py-1.5 bg-accent/40 border-b border-border">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                            Evaluation
                          </span>
                          <span className="text-[10px] text-muted-foreground/60">
                            {formatShortDate(runDateIso(latestRun))}
                          </span>
                        </div>
                        <div className="flex items-center gap-0 divide-x divide-border">
                          <div className="flex-1 px-2.5 py-2">
                            <p className="text-[10px] text-muted-foreground mb-0.5">Score</p>
                            <p className="text-xs text-foreground font-mono tabular-nums">
                              {score === null ? '—' : score}
                              <span className="text-muted-foreground/40">/100</span>
                            </p>
                          </div>
                          <div className="flex-1 px-2.5 py-2">
                            <p className="text-[10px] text-muted-foreground mb-0.5">Test Cases</p>
                            <p
                              className={cn(
                                'text-xs font-mono tabular-nums',
                                totalExecutions === 0
                                  ? 'text-foreground'
                                  : allPassed
                                    ? 'text-green-400'
                                    : 'text-red-400'
                              )}
                            >
                              {totalExecutions === 0 ? (
                                '—'
                              ) : (
                                <>
                                  {passedCount}
                                  <span className="text-muted-foreground/40">
                                    /{totalExecutions}
                                  </span>
                                </>
                              )}
                            </p>
                          </div>
                        </div>
                      </div>
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
