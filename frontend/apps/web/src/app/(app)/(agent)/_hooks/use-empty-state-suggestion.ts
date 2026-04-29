'use client';

import { useMemo } from 'react';

const IMPROVE_PROMPT_MESSAGE = 'Review my agent prompt and suggest improvements.';
const CREATE_PROMPT_MESSAGE =
  'I want to create a system prompt for a Voice AI agent from scratch. Start the interview and guide me through the process.';

interface UseEmptyStateSuggestionArgs {
  enabled: boolean;
  hasPrompt: boolean;
  sendMessage: (content: string) => Promise<void>;
}

export interface EmptyStateSuggestion {
  label: string;
  onClick: () => void;
}

export function useEmptyStateSuggestion({
  enabled,
  hasPrompt,
  sendMessage,
}: UseEmptyStateSuggestionArgs): EmptyStateSuggestion | undefined {
  return useMemo(
    () =>
      enabled
        ? {
            label: hasPrompt ? 'Improve agent prompt' : 'Help me create agent',
            onClick: () => {
              void sendMessage(hasPrompt ? IMPROVE_PROMPT_MESSAGE : CREATE_PROMPT_MESSAGE);
            },
          }
        : undefined,
    [enabled, hasPrompt, sendMessage],
  );
}
