'use client';

import { GitBranch, Loader2, RefreshCw, Workflow } from 'lucide-react';
import { Badge } from '@workspace/ui/components/ui/badge';
import { Button } from '@workspace/ui/components/ui/button';
import { TabsContent } from '@workspace/ui/components/ui/tabs';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAgentFlowStaleness } from '@/app/(app)/(agent)/_hooks/use-agent-flow-staleness';
import { useSyncAgentFlow } from '@/app/(app)/(agent)/_hooks/use-sync-agent-flow';

const TAB_VALUE = 'info';

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

export function InfoTab() {
  const { agentId, agent } = useAgentEditFormActions();
  // Reads the query the layout-level watcher already triggered once this
  // session — this does not fire a second request.
  const { data: staleness } = useAgentFlowStaleness(agentId, agent);
  const { sync, isPending: isSyncing, error: syncError } = useSyncAgentFlow(agentId);

  const metadata = (agent?.agent_metadata ?? {}) as Record<string, unknown>;
  const flowId = asString(metadata.conversation_flow_id);
  const flowVersion = asNumber(metadata.conversation_flow_version);
  const nodes = metadata.conversation_flow_nodes;
  const nodeCount = Array.isArray(nodes) ? nodes.length : null;
  const hasGlobalPrompt = Boolean(metadata.conversation_flow_global_prompt);
  const toolCount = agent?.tools?.length ?? 0;
  const platformAgentName = agent?.platform_agent_name ?? null;

  const rows: { label: string; value: string }[] = [
    { label: 'Source', value: 'Retell Conversation Flow' },
    ...(platformAgentName
      ? [{ label: 'Retell agent', value: platformAgentName }]
      : []),
    ...(flowId ? [{ label: 'Flow ID', value: flowId }] : []),
    ...(flowVersion !== null
      ? [
          {
            label: 'Flow version',
            value:
              staleness?.is_stale && staleness.live_version !== null
                ? `v${flowVersion} → v${staleness?.live_version}`
                : `v${flowVersion}`,
          },
        ]
      : []),
    ...(nodeCount !== null
      ? [{ label: 'Nodes', value: String(nodeCount) }]
      : []),
    { label: 'Tools', value: String(toolCount) },
    { label: 'Global prompt', value: hasGlobalPrompt ? 'Yes' : 'No' },
  ];

  return (
    <TabsContent value={TAB_VALUE} className="flex-1 mt-0 overflow-auto p-6">
      <div className="max-w-xl space-y-4">
        {staleness?.is_stale ? (
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
            <RefreshCw className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div className="space-y-2 flex-1 min-w-0">
              <div>
                <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
                  Flow updated in Retell
                  {staleness.captured_version !== null &&
                  staleness.live_version !== null
                    ? ` (v${staleness.captured_version} → v${staleness.live_version})`
                    : ''}
                </p>
                <p className="text-xs text-amber-800/80 dark:text-amber-300/70">
                  The version captured here is out of date. Sync to pull the
                  latest flow, publish a new version, and refresh requirements.
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 h-7 text-xs"
                onClick={() => sync()}
                disabled={isSyncing}
              >
                {isSyncing ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                {isSyncing ? 'Syncing…' : 'Sync Now'}
              </Button>
              {syncError ? (
                <p className="text-xs text-destructive">{syncError}</p>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="flex items-start gap-3 rounded-lg border border-border p-4">
          <Workflow className="w-5 h-5 text-muted-foreground mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium">Conversation Flow agent</p>
              <Badge variant="outline" className="text-[10px] py-0 px-1.5 h-4">
                Read-only
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              This agent&apos;s behavior lives in a Retell conversation flow — a
              graph of nodes rather than a single prompt. It can&apos;t be edited
              here. Connexity uses it to generate test cases from the extracted{' '}
              <span className="font-medium">Requirements</span> and to run
              evaluations against the live flow.
            </p>
          </div>
        </div>

        <dl className="rounded-lg border border-border divide-y divide-border">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-center justify-between px-4 py-2.5"
            >
              <dt className="text-xs text-muted-foreground">{row.label}</dt>
              <dd className="text-xs font-medium text-foreground truncate max-w-[60%] text-right">
                {row.value}
              </dd>
            </div>
          ))}
        </dl>

        <p className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
          <GitBranch className="w-3 h-3" />
          To change behavior, edit the flow in Retell, then use Sync Now above to
          refresh this agent.
        </p>
      </div>
    </TabsContent>
  );
}
