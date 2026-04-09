'use client';

import { useState } from 'react';

import {
  makeDefaultAuthHeader,
  makeDefaultParam,
  makeDefaultTool,
} from '@/app/(app)/(agent)/_schemas/agent-form';

import type {
  AgentToolValues,
  AuthHeaderValues,
  HttpMethod,
  ToolParameterValues,
} from '@/app/(app)/(agent)/_schemas/agent-form';

/**
 * Manages local state for a single tool being drafted/edited before it is
 * committed to the parent agent form. This keeps the in-progress edits
 * isolated so incomplete tools don't pollute the saved form state.
 *
 * Used by `DraftToolEditor` inside the tools tab.
 */
export function useDraftTool() {
  // Initialize with a blank tool using the schema defaults.
  const [draft, setDraft] = useState<AgentToolValues>(makeDefaultTool);

  /**
   * Generic setter – immutably updates a single top-level key on the draft.
   * All specialized setters below delegate to this.
   */
  const set = <K extends keyof AgentToolValues>(key: K, value: AgentToolValues[K]) =>
    setDraft((prev) => ({ ...prev, [key]: value }));

  // ── Scalar field setters ───────────────────────────────────────────────

  const setToolName = (value: string) => set('name', value);
  const setMethod = (value: HttpMethod) => set('method', value);

  // ── Auth header CRUD ───────────────────────────────────────────────────

  /** Append a new empty auth header entry to the list. */
  const addAuthHeader = () => set('authHeaders', [...draft.authHeaders, makeDefaultAuthHeader()]);

  /** Remove the auth header at `index`. */
  const removeAuth = (index: number) =>
    set(
      'authHeaders',
      draft.authHeaders.filter((_, i) => i !== index)
    );

  /** Partially update the auth header at `index` (merge semantics). */
  const updateAuthHeader = (index: number, patch: Partial<AuthHeaderValues>) =>
    set(
      'authHeaders',
      draft.authHeaders.map((h, i) => (i === index ? { ...h, ...patch } : h))
    );

  // ── Parameter CRUD ─────────────────────────────────────────────────────

  /** Append a new empty parameter entry to the list. */
  const addParameter = () => set('parameters', [...draft.parameters, makeDefaultParam()]);

  /** Remove the parameter at `index`. */
  const removeParameter = (index: number) =>
    set(
      'parameters',
      draft.parameters.filter((_, i) => i !== index)
    );

  /** Partially update the parameter at `index` (merge semantics). */
  const updateParameter = (index: number, patch: Partial<ToolParameterValues>) =>
    set(
      'parameters',
      draft.parameters.map((p, i) => (i === index ? { ...p, ...patch } : p))
    );

  return {
    draft,
    set,
    setToolName,
    setMethod,
    addAuthHeader,
    removeAuth,
    updateAuthHeader,
    addParameter,
    removeParameter,
    updateParameter,
  };
}
