'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createRun } from '@/actions/eval-configs';
import { runKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { RunCreate } from '@/client/types.gen';

interface UseCreateRunVariables {
  body: RunCreate;
  autoExecute?: boolean;
}

export function useCreateRun(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ body, autoExecute = true }: UseCreateRunVariables) => {
      const result = await createRun(body, autoExecute);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.list(agentId) });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
