'use client';

import { useCallback, useState } from 'react';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { PromptEditorService } from '@/client/sdk.gen';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { promptEditorKeys } from '@/constants/query-keys';
import { getApiErrorMessage } from '@/utils/error';

import type { PromptEditorSessionPublic } from '@/client/types.gen';

/**
 * Resolves the last-active prompt-editor session for the given agent.
 *
 * An agent can have many sessions. On mount we load the newest active
 * session (ordered by `updated_at` on the backend). If none exists the
 * panel renders empty and a session is created lazily when the user
 * sends their first message.
 *
 * `startNewSession` is a purely local clear — it hides the current
 * session from the UI so the next `sendMessage` call falls through to
 * `createSession`, which then writes a fresh row to the database.
 * Previous sessions are preserved.
 */
export function usePromptEditorSession(agentId: string) {
  const queryClient = useQueryClient();
  const { flushDraftSave } = useAgentEditFormActions();

  const [pendingNew, setPendingNew] = useState(false);

  const query = useQuery({
    queryKey: promptEditorKeys.session(agentId),
    queryFn: async (): Promise<PromptEditorSessionPublic | null> => {
      const list = await PromptEditorService.promptEditorListSessions({
        query: { agent_id: agentId, skip: 0, limit: 1 },
      });
      if (list.error || !list.data) {
        throw new Error(
          `Failed to list sessions: ${getApiErrorMessage(list.error)}`
        );
      }

      const newest = list.data.data[0];
      if (!newest || newest.status === 'archived') return null;
      return newest;
    },
    staleTime: Infinity,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: async (): Promise<PromptEditorSessionPublic> => {
      await flushDraftSave();

      const created = await PromptEditorService.promptEditorCreateSession({
        body: { agent_id: agentId },
      });
      if (created.error || !created.data) {
        throw new Error(
          `Failed to create session: ${getApiErrorMessage(created.error)}`
        );
      }
      return created.data;
    },
    onSuccess: (created) => {
      queryClient.setQueryData(promptEditorKeys.session(agentId), created);
      setPendingNew(false);
    },
  });

  const createSession = useCallback(async (): Promise<string> => {
    const created = await createMutation.mutateAsync();
    return created.id;
  }, [createMutation]);

  const startNewSession = useCallback(() => {
    setPendingNew(true);
  }, []);

  const clearStaleSession = useCallback(() => {
    queryClient.removeQueries({ queryKey: promptEditorKeys.session(agentId) });
    setPendingNew(true);
  }, [queryClient, agentId]);

  const effectiveSession = pendingNew ? null : query.data ?? null;

  return {
    sessionId: effectiveSession?.id ?? null,
    basePrompt: effectiveSession?.base_prompt ?? null,
    editedPrompt: effectiveSession?.edited_prompt ?? null,
    isLoading: query.isLoading,
    error: query.error,
    createSession,
    startNewSession,
    clearStaleSession,
    isCreating: createMutation.isPending,
  };
}
