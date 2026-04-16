'use client';

import { useCallback, useEffect, useRef } from 'react';

import { useUpsertDraft } from '@/app/(app)/(agent)/_hooks/use-upsert-draft';

// Standalone draft autosave hook for UI surfaces that mutate the draft
// outside react-hook-form (e.g. the editable diff view, where the form is in
// read-only "view historical version" mode and its `prompt` field holds the
// version being viewed — not the draft).
//
// Mirrors the 300ms debounce + dirty gating in agent-edit-form-context.tsx,
// and reuses the same useUpsertDraft mutation so the draft query + has_draft
// flag stay in sync.
export function useDraftAutosave(agentId: string) {
  const { mutate, isPending, error } = useUpsertDraft(agentId);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = useRef<string | null>(null);

  const schedule = useCallback(
    (systemPrompt: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        if (systemPrompt === lastSavedRef.current) return;
        lastSavedRef.current = systemPrompt;
        mutate({ system_prompt: systemPrompt });
      }, 300);
    },
    [mutate]
  );

  const flush = useCallback(
    (systemPrompt: string) => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (systemPrompt === lastSavedRef.current) return;
      lastSavedRef.current = systemPrompt;
      mutate({ system_prompt: systemPrompt });
    },
    [mutate]
  );

  // Seed the last-saved baseline with the server value so the first schedule()
  // call after mount doesn't immediately re-save an unchanged draft.
  const primeBaseline = useCallback((systemPrompt: string) => {
    lastSavedRef.current = systemPrompt;
  }, []);

  // Exposes the last value we successfully handed to mutate(). Callers use
  // this to distinguish a server echo (post-save query invalidation re-sends
  // the value we just saved) from a genuine external update, so they can
  // suppress clobbering in-progress edits.
  const getLastSaved = useCallback((): string | null => lastSavedRef.current, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return { schedule, flush, primeBaseline, getLastSaved, isPending, error };
}
