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
};

export const promptEditorKeys = {
  session: (agentId: string) => ['prompt-editor-session', agentId] as const,
  messages: (sessionId: string) => ['prompt-editor-messages', sessionId] as const,
};
