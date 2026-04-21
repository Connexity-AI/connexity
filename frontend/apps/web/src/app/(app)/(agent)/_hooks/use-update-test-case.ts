'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateTestCase } from '@/actions/test-cases';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { testCaseKeys } from '@/constants/query-keys';

import type { TestCaseUpdate } from '@/client/types.gen';

interface UpdateTestCaseVariables {
  testCaseId: string;
  body: TestCaseUpdate;
}

export function useUpdateTestCase(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ testCaseId, body }: UpdateTestCaseVariables) => {
      const result = await updateTestCase(testCaseId, body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
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
