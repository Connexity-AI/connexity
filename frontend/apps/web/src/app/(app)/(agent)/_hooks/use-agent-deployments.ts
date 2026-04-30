'use client';

import { useQuery } from '@tanstack/react-query';

import { listAgentDeployments } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useAgentDeployments(agentId: string) {
  return useQuery({
    queryKey: environmentKeys.agentDeployments(agentId),
    queryFn: async () => {
      const result = await listAgentDeployments(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch deployments');
      return result.data;
    },
    staleTime: 30 * 1000,
  });
}
