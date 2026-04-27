'use client';

import { useQuery } from '@tanstack/react-query';

import { listRetellAgents } from '@/actions/integrations';
import { retellAgentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useRetellAgents(integrationId: string | null) {
  return useQuery({
    queryKey: retellAgentKeys.byIntegration(integrationId ?? ''),
    enabled: !!integrationId,
    queryFn: async () => {
      const result = await listRetellAgents(integrationId!);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch Retell agents');
      return result.data;
    },
    staleTime: 30 * 1000,
  });
}
