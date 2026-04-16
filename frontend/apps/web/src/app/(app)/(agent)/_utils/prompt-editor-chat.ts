import { promptEditorKeys } from '@/constants/query-keys';

import type { ChatMessage } from '@/app/(app)/(agent)/_schemas/prompt-editor-chat-sse';
import type { PromptEditorMessagePublic, PromptEditorMessagesPublic } from '@/client/types.gen';
import type { QueryClient } from '@tanstack/react-query';

/** Map backend rows to the UI-facing chat message shape. */
export function toChatMessages(rows: PromptEditorMessagePublic[]): ChatMessage[] {
  return rows.map((message) => ({
    id: message.id,
    role: message.role === 'assistant' ? 'assistant' : 'user',
    content: message.content,
    createdAt: message.created_at,
  }));
}

export function makeUserBubble(content: string, createdAt: string): ChatMessage {
  return {
    id: `live-user-${Date.now()}`,
    role: 'user',
    content,
    createdAt,
  };
}

export function makeAssistantBubble(id: string, createdAt: string): ChatMessage {
  return {
    id,
    role: 'assistant',
    content: '',
    createdAt,
    isStreaming: true,
  };
}

/**
 * Pre-seed the messages query cache with an empty list so the auto-fetch
 * triggered by a `null → sessionId` transition doesn't race with an
 * immediately-following SSE POST and duplicate an optimistic user bubble.
 */
export function seedEmptyMessagesCache(queryClient: QueryClient, sessionId: string): void {
  queryClient.setQueryData<PromptEditorMessagesPublic>(
    promptEditorKeys.messages(sessionId),
    { data: [], count: 0 }
  );
}

/**
 * Optimistically mirror a completed turn into the persisted cache so the
 * hand-off from live bubbles to the persisted list is seamless. The synthetic
 * user row is replaced by the real row on the next `invalidateQueries`
 * (real id + server timestamp).
 */
export function appendTurnToMessagesCache({
  queryClient,
  sessionId,
  userContent,
  userCreatedAt,
  assistantMessage,
}: {
  queryClient: QueryClient;
  sessionId: string;
  userContent: string;
  userCreatedAt: string;
  assistantMessage: PromptEditorMessagePublic;
}): void {
  queryClient.setQueryData<PromptEditorMessagesPublic>(
    promptEditorKeys.messages(sessionId),
    (old) => {
      const existing = old?.data ?? [];
      const syntheticUser: PromptEditorMessagePublic = {
        id: `synthetic-user-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: userContent,
        created_at: userCreatedAt,
      };
      return {
        data: [...existing, syntheticUser, assistantMessage],
        count: existing.length + 2,
      };
    }
  );
}
