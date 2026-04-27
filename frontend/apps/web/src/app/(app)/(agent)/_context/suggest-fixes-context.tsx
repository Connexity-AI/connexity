'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

export interface SuggestFixesCaseSummary {
  testCaseResultId: string;
  testCaseId: string;
  testCaseName: string;
  passed: boolean | null;
  overallScore: number | null;
}

export interface SuggestFixesAttachment {
  runId: string;
  testCaseResultIds: string[];
  caseSummaries: SuggestFixesCaseSummary[];
}

interface SuggestFixesContextValue {
  attachment: SuggestFixesAttachment | null;
  setAttachment: (attachment: SuggestFixesAttachment) => void;
  removeCase: (testCaseResultId: string) => void;
  clear: () => void;
}

const SuggestFixesContext = createContext<SuggestFixesContextValue | null>(null);

export function useSuggestFixes() {
  const ctx = useContext(SuggestFixesContext);
  if (!ctx) {
    throw new Error('useSuggestFixes must be used within SuggestFixesProvider');
  }
  return ctx;
}

interface SuggestFixesProviderProps {
  children: ReactNode;
}

export function SuggestFixesProvider({ children }: SuggestFixesProviderProps) {
  const [attachment, setAttachmentState] = useState<SuggestFixesAttachment | null>(null);

  const setAttachment = useCallback((next: SuggestFixesAttachment) => {
    setAttachmentState(next);
  }, []);

  const clear = useCallback(() => {
    setAttachmentState(null);
  }, []);

  const removeCase = useCallback((testCaseResultId: string) => {
    setAttachmentState((prev) => {
      if (!prev) return prev;

      const nextIds = prev.testCaseResultIds.filter((id) => id !== testCaseResultId);

      if (nextIds.length === 0) return null;

      return {
        runId: prev.runId,
        testCaseResultIds: nextIds,
        caseSummaries: prev.caseSummaries.filter((s) => s.testCaseResultId !== testCaseResultId),
      };
    });
  }, []);

  const value = useMemo<SuggestFixesContextValue>(
    () => ({
      attachment,
      setAttachment,
      removeCase,
      clear,
    }),
    [attachment, setAttachment, removeCase, clear]
  );

  return <SuggestFixesContext.Provider value={value}>{children}</SuggestFixesContext.Provider>;
}
