'use client';

import { useCallback, useEffect, useRef } from 'react';

import { useSuggestFixes } from '@/app/(app)/(agent)/_context/suggest-fixes-context';

import type { SuggestFixesAttachment } from '@/app/(app)/(agent)/_context/suggest-fixes-context';
import type { SendMessageOptions } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-chat';

// Mirrors the backend `suggest_from_evals` preset copy. Used when the user
// hits Send with attachments present but no typed message.
const SUGGEST_FROM_EVALS_MESSAGE =
  'Analyze the eval results for this agent and suggest targeted prompt improvements to address the attached failing test cases and low-scoring metrics.';

interface UseSuggestFixesHandoffArgs {
  sessionId: string | null;
  sessionRunId: string | null;
  startNewSession: () => void;
}

interface PreparedSend {
  effectiveContent: string;
  extras: Required<
    Pick<SendMessageOptions, 'runId' | 'testCaseResultIds' | 'forceNewSession'>
  >;
}

export interface UseSuggestFixesHandoffResult {
  attachment: SuggestFixesAttachment | null;
  /**
   * Resolve the effective message content and send extras for a given turn,
   * then clear the attachment block so a follow-up send in the (now run-bound)
   * session doesn't re-ship the same ids. The user can re-attach from the
   * run detail page.
   */
  consume: (typedContent: string) => PreparedSend;
}

export function useSuggestFixesHandoff({
  sessionId,
  sessionRunId,
  startNewSession,
}: UseSuggestFixesHandoffArgs): UseSuggestFixesHandoffResult {
  const { attachment, clear } = useSuggestFixes();

  // When a fresh Suggest Fixes attachment arrives (handed off from the eval
  // run detail page via the hydrator), clear the currently displayed session
  // so the chat opens empty. The run-bound session is created lazily on the
  // first send via createSession({ runId }). The ref keys on the attachment
  // content so re-renders don't retrigger, but a different set of ids (new
  // handoff) will.
  const lastAttachmentKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const key = attachment
      ? `${attachment.runId}:${attachment.testCaseResultIds.join(',')}`
      : null;
    if (key && key !== lastAttachmentKeyRef.current) {
      startNewSession();
    }
    lastAttachmentKeyRef.current = key;
  }, [attachment, startNewSession]);

  const consume = useCallback(
    (typedContent: string): PreparedSend => {
      // Substitute a default message when the user hits Send with attachments
      // present but nothing typed — the attached cases are the context.
      const effectiveContent =
        typedContent.trim().length === 0 && attachment
          ? SUGGEST_FROM_EVALS_MESSAGE
          : typedContent;

      // Force a new session whenever the attachment's run doesn't match the
      // current session's run binding. Covers both an unbound existing session
      // (sessionRunId = null) and a session bound to a different run.
      const forceNewSession =
        !!attachment && !!sessionId && sessionRunId !== attachment.runId;

      const extras = {
        runId: attachment?.runId ?? null,
        testCaseResultIds: attachment?.testCaseResultIds ?? null,
        forceNewSession,
      };

      if (attachment) {
        clear();
      }

      return { effectiveContent, extras };
    },
    [attachment, sessionId, sessionRunId, clear],
  );

  return { attachment, consume };
}
