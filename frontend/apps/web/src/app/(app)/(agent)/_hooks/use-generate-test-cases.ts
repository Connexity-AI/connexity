'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { generateTestCases } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useGenerateTestCases(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (count: number) =>
      generateTestCases({ agent_id: agentId, count, persist: true }),

    onSettled: () => {
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
