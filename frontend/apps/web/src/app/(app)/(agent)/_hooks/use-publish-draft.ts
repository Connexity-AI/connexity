'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { publishAgentDraft } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { PublishRequest } from '@/client/types.gen';

export function usePublishDraft(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (body: PublishRequest) => publishAgentDraft(agentId, body),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      queryClient.invalidateQueries({ queryKey: ['agent-versions', agentId] });
      queryClient.invalidateQueries({ queryKey: ['agent', agentId] });
      queryClient.invalidateQueries({ queryKey: ['agent-draft', agentId] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
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
