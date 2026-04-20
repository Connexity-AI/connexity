'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { generateTestCases } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useGenerateTestCases(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (count: number) => {
      console.info('[gen-tc] request →', { agentId, count });
      const result = await generateTestCases({ agent_id: agentId, count, persist: true });
      console.info('[gen-tc] response ←', result);
      return result;
    },

    onError: (error) => {
      console.error('[gen-tc] mutation error', error);
    },

    onSettled: (data) => {
      if (data && isErrorApiResult(data)) {
        console.error('[gen-tc] API error', data.error);
      }
      queryClient.invalidateQueries({ queryKey: testCaseKeys.list(agentId) });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    mutate: mutation.mutate,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error,
  };
}
