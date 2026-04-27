'use client';

import { useCallback, useState } from 'react';

import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAiSuggestion } from '@/app/(app)/(agent)/_context/ai-suggestion-context';
import { useEmptyStateSuggestion } from '@/app/(app)/(agent)/_hooks/use-empty-state-suggestion';
import { usePromptEditorChat } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-chat';
import { usePromptEditorSession } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-session';
import { useSuggestFixesHandoff } from '@/app/(app)/(agent)/_hooks/use-suggest-fixes-handoff';
import { DEFAULT_ASSISTANT_MODEL_ID } from '@/config/assistant-models';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

export function useAgentChatbot() {
  const { agentId } = useAgentEditFormActions();

  const {
    sessionId,
    sessionRunId,
    basePrompt,
    isLoading: isSessionLoading,
    error: sessionError,
    createSession,
    startNewSession,
    clearStaleSession,
    updateBasePrompt,
    isCreating: isCreatingSession,
  } = usePromptEditorSession(agentId);

  const { suggestedPrompt, setSuggestion, setLiveEditedPrompt } = useAiSuggestion();

  const handoff = useSuggestFixesHandoff({ sessionId, sessionRunId, startNewSession });

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
      const formPrompt = form.getValues().prompt ?? '';

      // When there's an unsaved AI suggestion from a previous turn, use it
      // as the starting point so multi-turn edits accumulate correctly.
      // Otherwise fall back to the form value (the saved/manual prompt).
      const currentPrompt = suggestedPrompt ?? formPrompt;

      const { effectiveContent, extras } = handoff.consume(content);

      // Sync base_prompt with the textarea so the diff viewer shows only
      // the LLM's delta, not the user's prior manual edits attributed as
      // if the LLM made them. Skipped when no session exists yet — the
      // createSession path seeds base_prompt from the freshly-flushed draft.
      // Also skip when using an unsaved suggestion — the baseline should
      // stay anchored to the session start so cumulative diffs are shown.
      // Skip when forcing a fresh session — updating the old session's
      // baseline would be wasted work.
      if (
        !extras.forceNewSession &&
        !suggestedPrompt &&
        sessionId &&
        basePrompt !== null &&
        formPrompt !== basePrompt
      ) {
        await updateBasePrompt(formPrompt);
      }

      await underlyingSendMessage(effectiveContent, currentPrompt, model, extras);
    },
    [
      form,
      handoff,
      underlyingSendMessage,
      model,
      sessionId,
      basePrompt,
      updateBasePrompt,
      suggestedPrompt,
    ],
  );

  const suggestion = useEmptyStateSuggestion({
    enabled:
      !isHistoryLoading &&
      !isSessionLoading &&
      !sessionError &&
      messages.length === 0 &&
      !handoff.attachment,
    hasPrompt,
    sendMessage,
  });

  return {
    agentId,
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
    createNewSession: startNewSession,
    isCreatingSession,
  };
}
