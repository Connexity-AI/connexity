'use client';

import { useQuery } from '@tanstack/react-query';

import { getAgent } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';

import type { AgentPublic } from '@/client/types.gen';

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const result = await getAgent(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent');
      return result.data as AgentPublic;
    },
    staleTime: 30 * 1000,
  });
}
