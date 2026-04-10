'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createDraftAgent } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { agentKeys } from '@/constants/query-keys';

export function useCreateDraftAgent() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (name?: string) => createDraftAgent(name),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      queryClient.invalidateQueries({ queryKey: agentKeys.lists });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error,
  };
}
