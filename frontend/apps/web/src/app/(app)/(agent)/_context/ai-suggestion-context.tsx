'use client';

/**
 * AiSuggestionContext — live-edit preview state for AI-proposed prompt
 * changes. Pure client state: accept/decline are now local operations
 * (copy to form / clear), not server mutations.
 */

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

interface AiSuggestionContextValue {
  suggestedPrompt: string | null;
  setLiveEditedPrompt: (prompt: string) => void;
  setSuggestion: (prompt: string) => void;
  clearSuggestion: () => void;
}

const AiSuggestionContext = createContext<AiSuggestionContextValue | null>(null);

export function useAiSuggestion() {
  const ctx = useContext(AiSuggestionContext);
  if (!ctx) {
    throw new Error('useAiSuggestion must be used within AiSuggestionProvider');
  }
  return ctx;
}

interface AiSuggestionProviderProps {
  children: ReactNode;
}

export function AiSuggestionProvider({ children }: AiSuggestionProviderProps) {
  const [suggestedPrompt, setSuggestedPrompt] = useState<string | null>(null);

  const clearSuggestion = useCallback(() => {
    setSuggestedPrompt(null);
  }, []);

  const setLiveEditedPrompt = useCallback((prompt: string) => {
    setSuggestedPrompt(prompt);
  }, []);

  const setSuggestion = useCallback((prompt: string) => {
    setSuggestedPrompt(prompt);
  }, []);

  const value = useMemo<AiSuggestionContextValue>(
    () => ({
      suggestedPrompt,
      setLiveEditedPrompt,
      setSuggestion,
      clearSuggestion,
    }),
    [suggestedPrompt, setLiveEditedPrompt, setSuggestion, clearSuggestion]
  );

  return <AiSuggestionContext.Provider value={value}>{children}</AiSuggestionContext.Provider>;
}
