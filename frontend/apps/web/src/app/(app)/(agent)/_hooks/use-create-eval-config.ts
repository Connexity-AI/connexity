'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createEvalConfig } from '@/actions/eval-configs';
import { evalConfigKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { EvalConfigCreate } from '@/client/types.gen';

export function useCreateEvalConfig(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (body: EvalConfigCreate) => {
      const result = await createEvalConfig(body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evalConfigKeys.list(agentId) });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
