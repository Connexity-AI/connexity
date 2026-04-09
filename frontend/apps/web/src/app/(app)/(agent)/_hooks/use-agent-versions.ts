'use client';

import { useQuery } from '@tanstack/react-query';

import { getAgentVersions } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';

import type { AgentVersionsPublic } from '@/client/types.gen';

export function useAgentVersions(agentId: string) {
  return useQuery({
    queryKey: ['agent-versions', agentId],
    queryFn: async () => {
      const result = await getAgentVersions(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent versions');
      return result.data as unknown as AgentVersionsPublic;
    },
    staleTime: 30 * 1000,
  });
}
