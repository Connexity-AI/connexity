'use client';

import { useQuery } from '@tanstack/react-query';

import { listEnvironmentDeployments } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useEnvironmentDeployments(environmentId: string) {
  return useQuery({
    queryKey: environmentKeys.deployments(environmentId),
    queryFn: async () => {
      const result = await listEnvironmentDeployments(environmentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch deployments');
      return result.data;
    },
    staleTime: 30 * 1000,
  });
}
