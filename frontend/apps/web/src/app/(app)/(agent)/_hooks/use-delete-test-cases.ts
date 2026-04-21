'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deleteTestCase } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useDeleteTestCases(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (testCaseIds: string[]) => {
      const results = await Promise.all(testCaseIds.map((id) => deleteTestCase(id)));
      const firstError = results.find((result) => isErrorApiResult(result));
      if (firstError && isErrorApiResult(firstError)) {
        throw new Error(getApiErrorMessage(firstError.error));
      }
      return testCaseIds;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: testCaseKeys.list(agentId) });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
