'use client';

import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createDraftAgent } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { agentKeys } from '@/constants/query-keys';

export function useCreateDraftAgent() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: (name?: string) => createDraftAgent(name),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      router.push(UrlGenerator.agentEdit(result.data.id));

      queryClient.invalidateQueries({ queryKey: agentKeys.lists });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  const handleCreate = () => {
    mutation.mutate(undefined);
  };

  return {
    handleCreate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error,
  };
}
