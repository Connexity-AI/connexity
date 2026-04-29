'use client';

import { useCallback, useMemo, useRef, useState } from 'react';

import { useQueryClient } from '@tanstack/react-query';

import { client } from '@/client/client.gen';
import { promptEditorKeys } from '@/constants/query-keys';
import { sseEventSchema } from '@/app/(app)/(agent)/_schemas/prompt-editor-chat-sse';
import {
  appendTurnToMessagesCache,
  makeAssistantBubble,
  makeUserBubble,
  seedEmptyMessagesCache,
  toChatMessages,
} from '@/app/(app)/(agent)/_utils/prompt-editor-chat';
import { usePromptEditorMessages } from './use-prompt-editor-messages';

import type { ChatMessage, ChatPhase } from '@/app/(app)/(agent)/_schemas/prompt-editor-chat-sse';

export type { ChatMessage, ChatPhase };

type OnSuggestion = (args: { prompt: string; messageId: string }) => void;

interface UsePromptEditorChatArgs {
  sessionId: string | null;
  createSession: (args?: { runId?: string | null }) => Promise<string>;
  onSessionStale: () => void;
  onSuggestion: OnSuggestion;
  onEditedPrompt: (editedPrompt: string) => void;
}

export interface SendMessageOptions {
  runId?: string | null;
  testCaseResultIds?: string[] | null;
  /**
   * If true, discard the current `sessionId` and start a fresh session for
   * this turn — used when the current session's run binding doesn't match
   * the incoming Suggest Fixes attachment, so the backend loads aggregate
   * eval context for the correct run.
   */
  forceNewSession?: boolean;
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
  // Synchronous guard against re-entry. `phase`/`isStreaming` can't protect
  // the window before `createSession` resolves, so a double-click on the
  // suggestion button would otherwise fire two sendMessage calls in parallel.
  const inFlightRef = useRef(false);

  const persisted = useMemo(
    () => toChatMessages(messagesQuery.data?.data ?? []),
    [messagesQuery.data]
  );

  const messages: ChatMessage[] = useMemo(
    () => [...persisted, ...liveMessages],
    [persisted, liveMessages]
  );

  const isStreaming = phase === 'analyzing' || phase === 'editing';

  const sendMessage = useCallback(
    async (
      content: string,
      currentPrompt: string,
      model: string | null,
      options: SendMessageOptions = {},
    ) => {
      const trimmed = content.trim();
      if (!trimmed) return;
      if (inFlightRef.current) return;
      inFlightRef.current = true;

      try {
        setStreamError(null);
        latestEditedRef.current = null;

        let activeSessionId = sessionId;

        if (!activeSessionId || options.forceNewSession) {
          console.log('[chat] creating session', {
            reason: !activeSessionId ? 'none' : 'force',
            runId: options.runId ?? null,
          });
          try {
            activeSessionId = await createSession({ runId: options.runId ?? null });
            console.log('[chat] session created', { sessionId: activeSessionId });
            seedEmptyMessagesCache(queryClient, activeSessionId);
          } catch (error) {
            console.error('[chat] createSession failed', error);
            setStreamError(error instanceof Error ? error.message : 'Failed to create session');
            return;
          }
        }

        const now = new Date().toISOString();
        const userBubble = makeUserBubble(trimmed, now);
        const assistantId = `live-assistant-${Date.now()}`;
        streamingIdRef.current = assistantId;
        const assistantBubble = makeAssistantBubble(assistantId, now);

        setLiveMessages((previous) => [...previous, userBubble, assistantBubble]);
        setPhase('analyzing');

        let reasoningChunks = 0;
        let editEvents = 0;

        const handleSseEvent = (payload: { data: unknown; event?: string }) => {
          if (!payload.event) return;

          const parsed = sseEventSchema.safeParse(payload);
          if (!parsed.success) {
            console.warn('[chat] sse parse failed', {
              event: payload.event,
              issues: parsed.error.issues,
            });
            return;
          }

          switch (parsed.data.event) {
            case 'status': {
              const nextPhase = parsed.data.data.phase;
              console.log('[chat] sse <- status', { phase: nextPhase });
              setPhase(nextPhase);
              return;
            }

            case 'reasoning': {
              const chunk = parsed.data.data.content;

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
              const editedPrompt = parsed.data.data.edited_prompt;

              editEvents += 1;

              if (editedPrompt !== currentPrompt) {
                latestEditedRef.current = editedPrompt;
                onEditedPrompt(editedPrompt);
              }

              return;
            }

            case 'done': {
              const doneData = parsed.data.data;
              const { message } = doneData;

              const rawFinalPrompt = doneData.edited_prompt ?? latestEditedRef.current;
              // Only surface a suggestion when the backend actually changed the
              // prompt. The backend echoes current_prompt unchanged on no-op
              // turns (e.g. when the LLM asks a clarifying question), so
              // falling through would spuriously open the diff viewer with
              // "No differences".
              const isActualChange =
                editEvents > 0 && rawFinalPrompt !== null && rawFinalPrompt !== currentPrompt;

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

              appendTurnToMessagesCache({
                queryClient,
                sessionId: activeSessionId!,
                userContent: trimmed,
                userCreatedAt: userBubble.createdAt,
                assistantMessage: message,
              });

              setLiveMessages([]);

              void queryClient.invalidateQueries({
                queryKey: promptEditorKeys.messages(activeSessionId!),
              });

              streamingIdRef.current = null;
              latestEditedRef.current = null;
              setPhase('complete');

              return;
            }

            case 'error': {
              const errorPayload = parsed.data.data;
              console.error('[chat] sse <- error', errorPayload);

              setStreamError(errorPayload.detail ?? errorPayload.code ?? 'Unknown error');
              setPhase('idle');

              return;
            }
          }
        };

        try {
          console.log('[chat] POST /messages', { sessionId: activeSessionId });

          const testCaseResultIds =
            options.testCaseResultIds && options.testCaseResultIds.length > 0
              ? options.testCaseResultIds
              : null;

          const { stream } = await client.sse.post({
            security: [
              { in: 'cookie', name: 'auth_cookie', type: 'apiKey' },
              { scheme: 'bearer', type: 'http' },
            ],

            url: '/api/v1/prompt-editor/sessions/{session_id}/messages',
            path: { session_id: activeSessionId },
            body: {
              content: trimmed,
              current_prompt: currentPrompt,
              model: model && model.trim() ? model : null,
              test_case_result_ids: testCaseResultIds,
            },
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

          setLiveMessages((previous) =>
            previous.filter((msg) => msg.id !== streamingIdRef.current)
          );

          streamingIdRef.current = null;
        }
      } finally {
        inFlightRef.current = false;
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
