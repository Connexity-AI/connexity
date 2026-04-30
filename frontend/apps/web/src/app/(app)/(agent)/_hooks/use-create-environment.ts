'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createEnvironment } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { EnvironmentCreate } from '@/client/types.gen';

export function useCreateEnvironment(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (body: EnvironmentCreate) => {
      const result = await createEnvironment(body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: environmentKeys.list(agentId) });
      void queryClient.invalidateQueries({ queryKey: environmentKeys.agentDeployments(agentId) });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
