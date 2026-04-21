'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createTestCase } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { TestCaseCreate } from '@/client/types.gen';

export function useCreateTestCase(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (body: TestCaseCreate) => {
      const result = await createTestCase(body);
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
