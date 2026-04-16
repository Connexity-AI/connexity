'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// Layout constants for the auto-resizing textarea. Kept here (not in the
// component) so the hook is self-contained and the values stay in sync with
// the height-math below.
const MAX_ROWS = 10;
const LINE_HEIGHT_PX = 24;
const PADDING_PX = 8;

interface UseChatInputArgs {
  onSend: (content: string) => void;
  disabled?: boolean;
}

/**
 * Owns the state + behavior for a chat-style textarea input:
 *
 * - controlled `value`
 * - auto-resize up to `MAX_ROWS` then switch to an internal scrollbar
 * - Enter submits, Shift+Enter inserts a newline
 * - `canSend` gate (non-empty + not disabled)
 *
 * The component that consumes this is purely presentational — it wires the
 * returned handlers onto the form/textarea and renders the send button.
 */
export function useChatInput({ onSend, disabled }: UseChatInputArgs) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wasDisabledRef = useRef<boolean>(disabled ?? false);

  // Refocus the textarea when the input re-enables after a streaming turn,
  // so the user can immediately type the next message without reaching for
  // the mouse. Only fires on the true→false transition to avoid stealing
  // focus on initial mount.
  useEffect(() => {
    if (wasDisabledRef.current && !disabled) {
      textareaRef.current?.focus();
    }
    wasDisabledRef.current = disabled ?? false;
  }, [disabled]);

  // Auto-resize: the only reliable way to size a textarea to its content is
  // to first collapse it (`height: auto`) so `scrollHeight` reflects the real
  // content height, then set `height` explicitly. We also toggle `overflowY`
  // to avoid a brief scrollbar flash while growing below the cap.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';

    // Empty input: snap back to the min-height defined by the component and
    // keep the scrollbar hidden. Without this, `scrollHeight` on an empty
    // textarea can still report a tall value on some browsers.
    if (!value) {
      textarea.style.overflowY = 'hidden';
      return;
    }

    const maxHeight = MAX_ROWS * LINE_HEIGHT_PX + PADDING_PX;
    if (textarea.scrollHeight > maxHeight) {
      // Past the cap — pin the height and let the textarea scroll internally.
      textarea.style.height = `${maxHeight}px`;
      textarea.style.overflowY = 'auto';
    } else {
      // Under the cap — match the content height and hide the scrollbar.
      textarea.style.height = `${textarea.scrollHeight}px`;
      textarea.style.overflowY = 'hidden';
    }
  }, [value]);

  const canSend = value.trim().length > 0 && !disabled;

  const submit = useCallback(() => {
    if (!canSend) return;
    onSend(value.trim());
    setValue('');
  }, [canSend, onSend, value]);

  const handleSubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      submit();
    },
    [submit]
  );

  // Enter submits; Shift+Enter falls through to the browser default so the
  // user can insert a newline in multi-line prompts.
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        submit();
      }
    },
    [submit]
  );

  const handleChange = useCallback((event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(event.target.value);
  }, []);

  return {
    value,
    textareaRef,
    canSend,
    handleChange,
    handleSubmit,
    handleKeyDown,
  };
}
