'use client';

import { useQuery } from '@tanstack/react-query';

import { listEnvironmentRetellVersions } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useEnvironmentRetellVersions(environmentId: string) {
  return useQuery({
    queryKey: environmentKeys.retellVersions(environmentId),
    queryFn: async () => {
      const result = await listEnvironmentRetellVersions(environmentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch Retell versions');
      return result.data;
    },
    staleTime: 30 * 1000,
  });
}
