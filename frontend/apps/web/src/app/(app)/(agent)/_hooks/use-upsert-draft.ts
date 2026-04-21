'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { upsertAgentDraft } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { agentKeys } from '@/constants/query-keys';

import type { AgentDraftUpdate } from '@/client/types.gen';

// Shared mutation key so every caller (form autosave, editable-diff autosave,
// …) appears under one roof in react-query. Consumers use useIsMutating with
// this key to show a single "Saving…" indicator regardless of which surface
// triggered the save.
export const agentDraftMutationKey = (agentId: string) => ['agent-draft', agentId] as const;

export function useUpsertDraft(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationKey: agentDraftMutationKey(agentId),
    mutationFn: (body: AgentDraftUpdate) => upsertAgentDraft(agentId, body),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      // Mark the agent and draft caches stale so the *next* fresh mount
      // (e.g. user navigates away and back) refetches and sees the saved
      // edits. `refetchType: 'none'` deliberately skips refetching the
      // currently mounted consumer — a refetch here would change the
      // `formSource` reference in agent-edit-form-context, reset
      // react-hook-form via its `values` prop, regenerate `useFieldArray`
      // IDs, and remount parameter / auth-header rows mid-type (dropping
      // input focus).
      queryClient.invalidateQueries({
        queryKey: agentKeys.draft(agentId),
        refetchType: 'none',
      });
      queryClient.invalidateQueries({
        queryKey: agentKeys.detail(agentId),
        refetchType: 'none',
      });
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
