'use client';

import { useMutation } from '@tanstack/react-query';

import { testEvaluationEngine } from '@/actions/eval-configs';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { EvaluationEngineTestRequest } from '@/client/types.gen';

export function useTestEvaluationEngine() {
  const mutation = useMutation({
    mutationFn: async (body: EvaluationEngineTestRequest) => {
      const result = await testEvaluationEngine(body);
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
