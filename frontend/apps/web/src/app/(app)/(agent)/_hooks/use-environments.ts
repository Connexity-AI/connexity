'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { listEnvironments } from '@/actions/environments';
import { isSuccessApiResult } from '@/utils/api';
import { environmentKeys } from '@/constants/query-keys';

export function useEnvironments(agentId: string) {
  return useSuspenseQuery({
    queryKey: environmentKeys.list(agentId),

    queryFn: async () => {
      const result = await listEnvironments(agentId);

      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch environments');
      return result.data;
    },
  });
}
