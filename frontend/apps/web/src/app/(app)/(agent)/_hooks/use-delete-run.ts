'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deleteRun } from '@/actions/runs';
import { runKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useDeleteRun(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (runId: string) => {
      const result = await deleteRun(runId);
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
    error: mutation.error?.message,
  };
}
