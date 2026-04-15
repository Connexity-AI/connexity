'use client';

import { useCallback, useMemo, useRef, useState } from 'react';

import { useQueryClient } from '@tanstack/react-query';

import { client } from '@/client/client.gen';
import { promptEditorKeys } from '@/constants/query-keys';
import { usePromptEditorMessages } from './use-prompt-editor-messages';

import type { PromptEditorMessagePublic } from '@/client/types.gen';

export type ChatPhase = 'idle' | 'analyzing' | 'editing' | 'complete';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  isStreaming?: boolean;
};

type SseEventPayload = {
  data: unknown;
  event?: string;
};

type StatusData = { message_id?: string; phase: ChatPhase };
type ReasoningData = { content: string };
type EditData = {
  edited_prompt: string;
  edit_index: number;
  total_edits: number;
};
type DoneData = {
  message: PromptEditorMessagePublic;
  edited_prompt: string;
  base_prompt: string;
};
type ErrorData = { code: string; detail: string };

type OnSuggestion = (args: { prompt: string; messageId: string }) => void;

interface UsePromptEditorChatArgs {
  sessionId: string | null;
  createSession: () => Promise<string>;
  onSessionStale: () => void;
  onSuggestion: OnSuggestion;
  onEditedPrompt: (editedPrompt: string) => void;
}

export function usePromptEditorChat({
  sessionId,
  createSession,
  onSessionStale,
  onSuggestion,
  onEditedPrompt,
}: UsePromptEditorChatArgs) {
  const queryClient = useQueryClient();
  const messagesQuery = usePromptEditorMessages(sessionId);

  const [phase, setPhase] = useState<ChatPhase>('idle');
  const [streamError, setStreamError] = useState<string | null>(null);
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);

  const streamingIdRef = useRef<string | null>(null);
  const latestEditedRef = useRef<string | null>(null);

  const persisted: ChatMessage[] = useMemo(() => {
    const rows = messagesQuery.data?.data ?? [];
    return rows.map((message) => ({
      id: message.id,
      role: (message.role === 'assistant' ? 'assistant' : 'user') as 'user' | 'assistant',
      content: message.content,
      createdAt: message.created_at,
    }));
  }, [messagesQuery.data]);

  const messages: ChatMessage[] = useMemo(
    () => [...persisted, ...liveMessages],
    [persisted, liveMessages]
  );

  const isStreaming = phase === 'analyzing' || phase === 'editing';

  const sendMessage = useCallback(
    async (content: string, currentPrompt: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      setStreamError(null);
      latestEditedRef.current = null;

      let activeSessionId = sessionId;

      if (!activeSessionId) {
        console.log('[chat] no session, creating one');
        try {
          activeSessionId = await createSession();
          console.log('[chat] session created', { sessionId: activeSessionId });
        } catch (error) {
          console.error('[chat] createSession failed', error);
          setStreamError(error instanceof Error ? error.message : 'Failed to create session');
          return;
        }
      }

      const now = new Date().toISOString();

      const userBubble: ChatMessage = {
        id: `live-user-${Date.now()}`,
        role: 'user',
        content: trimmed,
        createdAt: now,
      };

      const assistantId = `live-assistant-${Date.now()}`;
      streamingIdRef.current = assistantId;

      const assistantBubble: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: now,
        isStreaming: true,
      };

      setLiveMessages((previous) => [...previous, userBubble, assistantBubble]);
      setPhase('analyzing');

      let reasoningChunks = 0;
      let editEvents = 0;

      const handleSseEvent = ({ data, event }: SseEventPayload) => {
        if (!event || typeof data !== 'object' || data === null) return;

        switch (event) {
          case 'status': {
            // TODO: discrimination union
            // TODO: remove console.logs
            const nextPhase = (data as StatusData).phase;

            console.log('[chat] sse <- status', { phase: nextPhase });
            if (nextPhase) setPhase(nextPhase);
            return;
          }

          case 'reasoning': {
            const chunk = (data as ReasoningData).content ?? '';

            reasoningChunks += 1;

            if (reasoningChunks === 1 || reasoningChunks % 20 === 0) {
              console.log('[chat] sse <- reasoning', {
                chunkIndex: reasoningChunks,
                chunkLen: chunk.length,
              });
            }

            setLiveMessages((previous) =>
              previous.map((message) =>
                message.id === streamingIdRef.current
                  ? { ...message, content: message.content + chunk }
                  : message
              )
            );
            return;
          }

          case 'edit': {
            const editData = data as EditData;

            const editedPrompt = editData.edited_prompt;

            editEvents += 1;

            console.log('[chat] sse <- edit', {
              editIndex: editData.edit_index,
              totalEdits: editData.total_edits,
              promptLen: typeof editedPrompt === 'string' ? editedPrompt.length : 0,
            });

            if (typeof editedPrompt === 'string' && editedPrompt !== currentPrompt) {
              latestEditedRef.current = editedPrompt;
              onEditedPrompt(editedPrompt);
            }

            return;
          }

          case 'done': {
            const doneData = data as DoneData;

            const { message } = doneData;

            const rawFinalPrompt = doneData.edited_prompt ?? latestEditedRef.current;
            // Only surface a suggestion when the backend actually changed the
            // prompt. The backend echoes current_prompt unchanged on no-op
            // turns (e.g. when the LLM asks a clarifying question), so
            // falling through would spuriously open the diff viewer with
            // "No differences".
            const isActualChange =
              editEvents > 0 && rawFinalPrompt !== null && rawFinalPrompt !== currentPrompt;
            console.log('[chat] sse <- done', {
              messageId: message.id,
              finalPromptLen: rawFinalPrompt?.length ?? 0,
              reasoningChunks,
              editEvents,
              isActualChange,
            });

            setLiveMessages((previous) =>
              previous.map((chatMessage) =>
                chatMessage.id === streamingIdRef.current
                  ? { ...chatMessage, content: message.content, isStreaming: false }
                  : chatMessage
              )
            );

            if (isActualChange) {
              onSuggestion({
                prompt: rawFinalPrompt,
                messageId: message.id,
              });
            }

            void queryClient.invalidateQueries({
              queryKey: promptEditorKeys.messages(activeSessionId!),
            });

            setLiveMessages([]);

            streamingIdRef.current = null;

            latestEditedRef.current = null;

            setPhase('complete');

            return;
          }

          case 'error': {
            const errorPayload = data as ErrorData;
            console.error('[chat] sse <- error', errorPayload);

            setStreamError(errorPayload.detail ?? errorPayload.code ?? 'Unknown error');

            setPhase('idle');

            return;
          }
        }
      };

      try {
        console.log('[chat] POST /messages', { sessionId: activeSessionId });

        const { stream } = await client.sse.post({
          security: [
            { in: 'cookie', name: 'auth_cookie', type: 'apiKey' },
            { scheme: 'bearer', type: 'http' },
          ],

          url: '/api/v1/prompt-editor/sessions/{session_id}/messages',
          path: { session_id: activeSessionId },
          body: { content: trimmed, current_prompt: currentPrompt },
          headers: { 'Content-Type': 'application/json' },

          onSseEvent: handleSseEvent,
          onSseError: (sseError) => {
            console.error('[chat] SSE error', sseError);
          },

          sseMaxRetryAttempts: 0,
        });

        let finished = false;

        while (!finished) {
          const { done } = await stream.next();
          if (done) finished = true;
        }

        console.log('[chat] stream drained', {
          sessionId: activeSessionId,
          reasoningChunks,
          editEvents,
        });
      } catch (error) {
        console.error('[chat] sendMessage caught error', error);

        const message = error instanceof Error ? error.message : 'Streaming failed';
        const isSessionGone = /SSE failed: 404\b/.test(message);

        if (isSessionGone) {
          onSessionStale();
          setStreamError('Previous chat session was removed. Please try again.');
        } else {
          setStreamError(message);
        }
        setPhase('idle');

        setLiveMessages((previous) => previous.filter((msg) => msg.id !== streamingIdRef.current));

        streamingIdRef.current = null;
      }
    },
    [sessionId, createSession, onSessionStale, onSuggestion, onEditedPrompt, queryClient]
  );

  return {
    messages,
    phase,
    isStreaming,
    streamError,
    sendMessage,
    isHistoryLoading: messagesQuery.isLoading,
  };
}
