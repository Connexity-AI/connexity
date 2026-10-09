'use client';

import { useState } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { useMutation, useQuery, useQueryClient, useSuspenseQuery } from '@tanstack/react-query';
import { Workflow } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { useIntegrations } from '@/app/(app)/(agent)/_hooks/use-integrations';
import { agentToolsQuery } from '@/app/(app)/(agent)/_queries/agent-tools-query';
import { clearToolBackend, listIntegrationWorkflows, setToolBackend } from '@/actions/integrations';
import { IntegrationProvider } from '@/client/types.gen';
import { isSuccessApiResult } from '@/utils/api';
import { integrationKeys } from '@/constants/query-keys';

import type { AgentToolPublic, IntegrationPublic } from '@/client/types.gen';

const SELECT_CLASS =
  'h-8 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-xs text-foreground disabled:opacity-50';

function errorDetail(result: unknown, fallback: string): string {
  if (typeof result === 'object' && result !== null && 'error' in result) {
    const error = (result as { error: unknown }).error;
    if (typeof error === 'object' && error !== null && 'detail' in error) {
      return String((error as { detail: unknown }).detail);
    }
  }
  return fallback;
}

interface ToolBackendsSectionProps {
  agentId: string;
}

export function ToolBackendsSection({ agentId }: ToolBackendsSectionProps) {
  const { data: integrations } = useIntegrations();
  const { data: tools } = useSuspenseQuery(agentToolsQuery(agentId));
  const connections = integrations.data.filter((item) => item.provider === IntegrationProvider.N8N);

  return (
    <section>
      <div className="mb-4 flex items-center gap-2">
        <Workflow className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-xs uppercase tracking-wider text-muted-foreground">Tool backends</h2>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">
        Which n8n workflow serves each tool. A tool call then opens to the workflow&apos;s
        execution. Leave a tool unmapped if it has no backend.
      </p>

      {connections.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
          No n8n connection yet. Add one on the{' '}
          <Link
            href={UrlGenerator.integrations()}
            className="text-foreground underline underline-offset-2"
          >
            Integrations page
          </Link>
          .
        </div>
      ) : tools.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
          No tool calls seen yet. Tools appear here once the agent&apos;s calls use them.
        </div>
      ) : (
        <ul className="space-y-2">
          {tools.map((tool) => (
            <ToolBackendRow
              key={tool.name}
              agentId={agentId}
              tool={tool}
              connections={connections}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

interface ToolBackendRowProps {
  agentId: string;
  tool: AgentToolPublic;
  connections: IntegrationPublic[];
}

function ToolBackendRow({ agentId, tool, connections }: ToolBackendRowProps) {
  const queryClient = useQueryClient();
  const onlyConnection = connections.length === 1 ? connections[0]?.id : undefined;
  const [connectionId, setConnectionId] = useState(
    tool.backend?.integration_id ?? onlyConnection ?? ''
  );
  const [isChoosing, setIsChoosing] = useState(false);

  const workflowsQuery = useQuery({
    queryKey: integrationKeys.workflows(connectionId),
    queryFn: async () => {
      const result = await listIntegrationWorkflows(connectionId);
      if (!isSuccessApiResult(result)) {
        throw new Error(errorDetail(result, 'Could not read the workflows'));
      }
      return result.data;
    },
    enabled: isChoosing && connectionId !== '',
    staleTime: 5 * 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: async (workflowId: string | null) => {
      if (workflowId === null) {
        const result = await clearToolBackend(agentId, tool.name);
        if (!isSuccessApiResult(result)) {
          throw new Error(errorDetail(result, 'Could not remove the mapping'));
        }
        return;
      }
      const result = await setToolBackend(agentId, {
        tool_name: tool.name,
        integration_id: connectionId,
        workflow_id: workflowId,
      });
      if (!isSuccessApiResult(result)) {
        throw new Error(errorDetail(result, 'Could not save the mapping'));
      }
    },
    onSuccess: () => setIsChoosing(false),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: integrationKeys.agentTools(agentId) }),
  });

  const error = mutation.error ?? workflowsQuery.error;

  return (
    <li className="rounded-lg border border-border p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-mono text-sm text-foreground">{tool.name}</p>
          <p className="text-[11px] text-muted-foreground">
            {tool.call_count} {tool.call_count === 1 ? 'call' : 'calls'}
            {tool.backend ? (
              <>
                {' · '}
                <span className="text-foreground/80">{tool.backend.workflow_name}</span>
                {' in '}
                {tool.backend.integration_name}
              </>
            ) : (
              ' · not mapped'
            )}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {tool.backend ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(null)}
            >
              Clear
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={mutation.isPending}
            onClick={() => setIsChoosing((open) => !open)}
          >
            {isChoosing ? 'Cancel' : tool.backend ? 'Change' : 'Map'}
          </Button>
        </div>
      </div>

      {isChoosing ? (
        <div className="mt-3 flex items-center gap-2">
          <select
            aria-label={`n8n connection for ${tool.name}`}
            className={SELECT_CLASS}
            value={connectionId}
            disabled={mutation.isPending}
            onChange={(event) => setConnectionId(event.target.value)}
          >
            <option value="">Choose a connection</option>
            {connections.map((connection) => (
              <option key={connection.id} value={connection.id}>
                {connection.name}
              </option>
            ))}
          </select>
          <select
            aria-label={`Workflow for ${tool.name}`}
            className={SELECT_CLASS}
            value=""
            disabled={connectionId === '' || workflowsQuery.isLoading || mutation.isPending}
            onChange={(event) => {
              if (event.target.value) mutation.mutate(event.target.value);
            }}
          >
            <option value="">
              {workflowsQuery.isLoading ? 'Reading workflows…' : 'Choose a workflow'}
            </option>
            {(workflowsQuery.data ?? []).map((workflow) => (
              <option key={workflow.id} value={workflow.id}>
                {workflow.name}
                {workflow.active ? '' : ' (inactive)'}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      {error ? <p className="mt-2 text-xs text-destructive">{error.message}</p> : null}
    </li>
  );
}
