'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { upsertAgentDraft } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { agentKeys } from '@/constants/query-keys';

import type { AgentDraftUpdate, AgentPublic } from '@/client/types.gen';

export function useUpsertDraft(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (body: AgentDraftUpdate) => upsertAgentDraft(agentId, body),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      queryClient.invalidateQueries({ queryKey: agentKeys.draft(agentId) });
      queryClient.setQueryData<AgentPublic>(agentKeys.detail(agentId), (old) =>
        old ? { ...old, has_draft: true } : old
      );
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
