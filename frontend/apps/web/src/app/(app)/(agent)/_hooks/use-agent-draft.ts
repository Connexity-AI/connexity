'use client';

import { useQuery } from '@tanstack/react-query';

import { getAgentDraft } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';

import type { AgentVersionPublic } from '@/client/types.gen';

export function useAgentDraft(agentId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['agent-draft', agentId],
    queryFn: async () => {
      const result = await getAgentDraft(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent draft');
      return result.data as unknown as AgentVersionPublic;
    },
    staleTime: 30 * 1000,
    enabled,
  });
}
