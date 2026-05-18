'use client';

import { useMutation } from '@tanstack/react-query';

import { testRuntime } from '@/actions/eval-configs';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { RuntimeTestRequest } from '@/client/types.gen';

export function useTestRuntime() {
  const mutation = useMutation({
    mutationFn: async (body: RuntimeTestRequest) => {
      const result = await testRuntime(body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },
  });

  return {
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
    reset: mutation.reset,
  };
}
