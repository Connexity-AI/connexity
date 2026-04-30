'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deleteEnvironment } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useDeleteEnvironment(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (environmentId: string) => {
      const result = await deleteEnvironment(environmentId);
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
