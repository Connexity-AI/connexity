'use client';

import { useQuery } from '@tanstack/react-query';

import { PromptEditorService } from '@/client/sdk.gen';
import { promptEditorKeys } from '@/constants/query-keys';

import type { PromptEditorMessagesPublic } from '@/client/types.gen';

/**
 * Hydrates the persisted message history for a prompt-editor session.
 *
 * Disabled until `sessionId` is resolved by `usePromptEditorSession`.
 * Invalidated by the chat hook after the SSE stream emits `done`.
 */
export function usePromptEditorMessages(sessionId: string | null) {
  return useQuery({
    queryKey: promptEditorKeys.messages(sessionId ?? '__none__'),
    queryFn: async (): Promise<PromptEditorMessagesPublic> => {
      if (!sessionId) throw new Error('sessionId is required');

      const result = await PromptEditorService.promptEditorListMessages({
        path: { session_id: sessionId },
        query: { skip: 0, limit: 200 },
      });

      if (result.error || !result.data) {
        throw new Error('Failed to list prompt-editor messages');
      }

      return result.data;
    },
    enabled: sessionId !== null,
    staleTime: 30 * 1000,
  });
}
