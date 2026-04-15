'use client';

import { useCallback, useMemo, useState } from 'react';

import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAiSuggestion } from '@/app/(app)/(agent)/_context/ai-suggestion-context';
import { usePromptEditorChat } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-chat';
import { usePromptEditorSession } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-session';
import { DEFAULT_ASSISTANT_MODEL_ID } from '@/config/assistant-models';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const IMPROVE_PROMPT_MESSAGE = 'Review my agent prompt and suggest improvements.';
const CREATE_PROMPT_MESSAGE = 'Help me create an agent prompt from scratch.';

export function useAgentChatbot() {
  const { agentId } = useAgentEditFormActions();

  const {
    sessionId,
    isLoading: isSessionLoading,
    error: sessionError,
    createSession,
    startNewSession,
    clearStaleSession,
    isCreating: isCreatingSession,
  } = usePromptEditorSession(agentId);

  const { setSuggestion, setLiveEditedPrompt } = useAiSuggestion();

  const [model, setModel] = useState<string>(DEFAULT_ASSISTANT_MODEL_ID);

  const form = useFormContext<AgentFormValues>();
  const draftPrompt = useWatch({ control: form.control, name: 'prompt' }) ?? '';
  const hasPrompt = draftPrompt.trim().length > 0;

  const onSuggestion = useCallback(
    ({ prompt }: { prompt: string; messageId: string }) => {
      setSuggestion(prompt);
    },
    [setSuggestion]
  );

  const {
    messages,
    phase,
    isStreaming,
    streamError,
    sendMessage: underlyingSendMessage,
    isHistoryLoading,
  } = usePromptEditorChat({
    sessionId,
    createSession,
    onSessionStale: clearStaleSession,
    onSuggestion,
    onEditedPrompt: setLiveEditedPrompt,
  });

  const sendMessage = useCallback(
    async (content: string) => {
      const currentPrompt = form.getValues().prompt ?? '';

      await underlyingSendMessage(content, currentPrompt);
    },
    [form, underlyingSendMessage]
  );

  const createNewSession = useCallback(() => {
    startNewSession();
  }, [startNewSession]);

  const showSuggestion =
    !isHistoryLoading && !isSessionLoading && !sessionError && messages.length === 0;

  const suggestion = useMemo(
    () =>
      showSuggestion
        ? {
            label: hasPrompt ? 'Improve agent prompt' : 'Help me create agent',
            onClick: () => {
              void sendMessage(hasPrompt ? IMPROVE_PROMPT_MESSAGE : CREATE_PROMPT_MESSAGE);
            },
          }
        : undefined,
    [showSuggestion, hasPrompt, sendMessage]
  );

  return {
    sessionId,
    isSessionLoading,
    sessionError,
    model,
    setModel,
    messages,
    phase,
    isStreaming,
    streamError,
    sendMessage,
    isHistoryLoading,
    suggestion,
    createNewSession,
    isCreatingSession,
  };
}
