'use client';

import { useQuery } from '@tanstack/react-query';

import { getAgentVersion } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';

import type { AgentVersionPublic } from '@/client/types.gen';

export function useAgentVersion(agentId: string, version: number | null) {
  return useQuery({
    queryKey: ['agent-version', agentId, version],
    queryFn: async () => {
      const result = await getAgentVersion(agentId, version!);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent version');
      return result.data as unknown as AgentVersionPublic;
    },
    staleTime: 30 * 1000,
    enabled: version !== null,
  });
}
