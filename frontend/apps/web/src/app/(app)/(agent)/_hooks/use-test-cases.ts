'use client';

import { useQuery } from '@tanstack/react-query';

import { listTestCases } from '@/actions/test-cases';
import { isSuccessApiResult } from '@/utils/api';
import { testCaseKeys } from '@/constants/query-keys';

export function useTestCases(agentId: string) {
  return useQuery({
    queryKey: testCaseKeys.list(agentId),

    queryFn: async () => {
      const result = await listTestCases(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch test cases');
      return result.data;
    },

    staleTime: 30 * 1000,
  });
}
