'use client';

import { createContext, useContext, useEffect, useRef, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { Form } from '@workspace/ui/components/ui/form';

import {
  agentFormSchema,
  agentFormDefaults,
  type AgentFormValues,
} from '@/app/(app)/(agent)/_schemas/agent-form';
import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useAgentDraft } from '@/app/(app)/(agent)/_hooks/use-agent-draft';
import { useAgentVersion } from '@/app/(app)/(agent)/_hooks/use-agent-version';
import { useUpsertDraft } from '@/app/(app)/(agent)/_hooks/use-upsert-draft';
import { useUpdateAgent } from '@/app/(app)/(agent)/_hooks/use-update-agent';
import { mapAgentToForm } from '@/app/(app)/(agent)/_utils/map-agent-to-form';
import { mapFormToDraft } from '@/app/(app)/(agent)/_utils/map-form-to-draft';
import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';

import type { ReactNode } from 'react';

// ─── Actions context ─────────────────────────────────────────────────────────
// Exposes form-level actions (submit, loading states, errors) to child
// components without coupling them to the form instance itself. Children
// consume this via `useAgentEditFormActions()` and never touch react-hook-form
// directly — only this provider interacts with the form.

interface AgentEditFormActions {
  onSubmit: () => void;
  isPending: boolean;
  error: string | null;
  agentName: string;
  isLoading: boolean;
  isReadOnly: boolean;
  isDraftSaving: boolean;
  agentId: string;
}

const AgentEditFormActionsContext = createContext<AgentEditFormActions | null>(null);

export function useAgentEditFormActions() {
  const ctx = useContext(AgentEditFormActionsContext);
  if (!ctx) {
    throw new Error('useAgentEditFormActions must be used within AgentEditFormProvider');
  }
  return ctx;
}

// ─── Provider ────────────────────────────────────────────────────────────────

interface AgentEditFormProviderProps {
  agentId: string;
  children: ReactNode;
}

export function AgentEditFormProvider({ agentId, children }: AgentEditFormProviderProps) {
  // ─── Data fetching ────────────────────────────────────────────────────────
  // Three possible data sources feed the form, in priority order:
  //   1. A specific historical version (when the user is browsing version history)
  //   2. An unsaved draft (when the agent has pending changes)
  //   3. The published agent (the baseline / live config)

  const { data: agent, isLoading: isAgentLoading } = useAgent(agentId);
  const { selectedVersion, isReadOnly, openPublishDialog } = useVersions();

  const { data: draft, isLoading: isDraftLoading } = useAgentDraft(
    agentId,
    agent?.has_draft === true
  );

  const { data: versionData, isLoading: isVersionLoading } = useAgentVersion(
    agentId,
    selectedVersion
  );

  // ─── Form source derivation ──────────────────────────────────────────────
  // useMemo is *required* here (not just an optimization). `mapAgentToForm`
  // returns a new object every call. Without memoisation, `useForm`'s
  // `values` prop receives a new reference on every render, which resets
  // the form, which triggers another render → infinite loop.
  const formSource = useMemo(() => {
    if (selectedVersion !== null && versionData) {
      return mapAgentToForm(versionData);
    }
    if (draft) {
      return mapAgentToForm(draft);
    }
    if (agent) {
      return mapAgentToForm(agent);
    }
    return undefined;
  }, [selectedVersion, versionData, draft, agent]);

  // `values` keeps the form in sync with the server data — whenever
  // `formSource` changes (e.g. draft loaded, version switched), react-hook-form
  // resets the form fields to match.
  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: agentFormDefaults,
    values: formSource,
  });

  const agentName = agent?.name ?? '';
  const { isPending: isUpdatePending, error: updateError } = useUpdateAgent(agentId, agentName);
  const { mutate: draftMutate, isPending: isDraftSaving } = useUpsertDraft(agentId);

  // ─── Auto-save to draft ──────────────────────────────────────────────────
  // Subscribes to every form change via `form.watch` and persists the values
  // as a draft after a 300ms debounce. We use `form.formState.isDirty` to
  // distinguish user edits from server-driven resets (the `values` prop).
  // When `values` updates (draft refetch, version switch), react-hook-form
  // resets the form and clears `isDirty`, so the save is skipped.

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isReadOnly) return;

    const subscription = form.watch(() => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(() => {
        // Only save when the user has actually modified the form.
        // `isDirty` is false after a `values` prop reset (server data sync).
        if (!form.formState.isDirty) return;

        const values = form.getValues();
        // Sanity check — prompt is the minimum required field for a valid draft.
        if (values.prompt !== undefined) {
          draftMutate(mapFormToDraft(values));
        }
      }, 300);
    });

    return () => {
      subscription.unsubscribe();
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [form, isReadOnly, draftMutate]);

  // ─── Submit (publish) ────────────────────────────────────────────────────
  // No useCallback needed — React Compiler handles memoisation for this
  // component. The function saves the current form as a draft (flushing any
  // pending debounced save first) and then opens the publish confirmation dialog.

  const onSubmit = () => {
    if (isReadOnly) return;

    // Cancel any in-flight debounced auto-save so we don't double-save or
    // overwrite the draft we're about to write synchronously.
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    // Validate → save draft → open publish dialog
    form.handleSubmit((data) => {
      draftMutate(mapFormToDraft(data), {
        onSuccess: () => openPublishDialog(),
      });
    })();
  };

  const isLoading =
    isAgentLoading || isDraftLoading || (selectedVersion !== null && isVersionLoading);

  return (
    <AgentEditFormActionsContext.Provider
      value={{
        onSubmit,
        isPending: isUpdatePending,
        error: updateError,
        agentName,
        isLoading,
        isReadOnly,
        isDraftSaving,
        agentId,
      }}
    >
      <Form {...form}>{children}</Form>
    </AgentEditFormActionsContext.Provider>
  );
}
