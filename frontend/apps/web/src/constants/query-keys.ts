import type { AgentFilters } from '@/actions/agents';

/**
 * Centralized TanStack Query key factory.
 * Use these helpers instead of hard-coded arrays so key strings can't drift
 * between `useQuery` call sites and `invalidateQueries` / `setQueryData` calls.
 */
export const agentKeys = {
  lists: ['agents'] as const,
  list: (filters: AgentFilters) => ['agents', filters] as const,
  detail: (agentId: string) => ['agent', agentId] as const,
  draft: (agentId: string) => ['agent-draft', agentId] as const,
  versions: (agentId: string) => ['agent-versions', agentId] as const,
  version: (agentId: string, version: number | null) =>
    ['agent-version', agentId, version] as const,
  guidelines: (agentId: string) => ['agent-guidelines', agentId] as const,
};

export const promptEditorKeys = {
  session: (agentId: string) => ['prompt-editor-session', agentId] as const,
  messages: (sessionId: string) => ['prompt-editor-messages', sessionId] as const,
};

export const testCaseKeys = {
  list: (agentId: string) => ['test-cases', agentId] as const,
};

export const integrationKeys = {
  all: ['integrations'] as const,
  list: () => ['integrations', 'list'] as const,
};

export const evalConfigKeys = {
  list: (agentId: string) => ['eval-configs', agentId] as const,
  detail: (evalConfigId: string) => ['eval-config', evalConfigId] as const,
};

export const metricKeys = {
  list: () => ['available-metrics'] as const,
};

export const runKeys = {
  list: (agentId: string) => ['runs', agentId] as const,
  detail: (runId: string) => ['run', runId] as const,
};

export const testCaseResultKeys = {
  byRun: (runId: string) => ['test-case-results', runId] as const,
};

export const environmentKeys = {
  list: (agentId: string) => ['environments', agentId] as const,
};

export const retellAgentKeys = {
  byIntegration: (integrationId: string) => ['retell-agents', integrationId] as const,
};

export type CallFilters = {
  page?: number;
  pageSize?: number;
  dateFrom?: string | null;
  dateTo?: string | null;
};

export const callKeys = {
  all: ['calls'] as const,
  list: (agentId: string, filters: CallFilters = {}) =>
    ['calls', agentId, filters] as const,
  detail: (callId: string) => ['call', callId] as const,
};
