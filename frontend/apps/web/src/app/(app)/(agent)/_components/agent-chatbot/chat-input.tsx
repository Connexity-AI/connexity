'use client';

import { Send, Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import { useChatInput } from '@/app/(app)/(agent)/_hooks/use-chat-input';
import { ModelSelector } from './model-selector';

interface SuggestionPill {
  label: string;
  onClick: () => void;
}

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  model: string;
  onModelChange: (model: string) => void;
  /** Optional suggestion chip shown above the input (e.g. "Improve agent prompt"). */
  suggestion?: SuggestionPill;
}

/**
 * Chat input area — suggestion pill + rounded input card with textarea and
 * bottom toolbar (model selector + send). Styled to match the
 * `Engineer Tool Layout` reference so the two chat surfaces stay in sync.
 *
 * All input behavior (auto-resize, Enter-to-send, canSend gating) lives in
 * the `useChatInput` hook — this component is purely presentational.
 */
export function ChatInput({
  onSend,
  disabled,
  model,
  onModelChange,
  suggestion,
}: ChatInputProps) {
  const { value, textareaRef, canSend, handleChange, handleSubmit, handleKeyDown } = useChatInput({
    onSend,
    disabled,
  });

  return (
    <div className="border-t border-border p-4 space-y-2.5 shrink-0">
      {/* Suggestion pill */}
      {suggestion && (
        <div className="flex">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={suggestion.onClick}
            disabled={disabled}
            className="h-auto gap-1.5 rounded-full border-border px-3 py-1.5 text-xs font-normal text-muted-foreground hover:border-foreground/30 hover:bg-accent/40 hover:text-foreground"
          >
            <Sparkles className="w-3 h-3 text-blue-400 shrink-0" />
            {suggestion.label}
          </Button>
        </div>
      )}

      {/* Input card */}
      <form
        onSubmit={handleSubmit}
        className={cn(
          'flex flex-col rounded-xl border border-input bg-transparent transition-shadow',
          'focus-within:ring-1 focus-within:ring-ring'
        )}
      >
        <Textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Thinking…' : 'Message the assistant…'}
          disabled={disabled}
          className="min-h-9 w-full resize-none overflow-y-hidden rounded-none border-0 bg-transparent px-3 pt-2.5 pb-1 text-sm leading-6 text-foreground shadow-none ring-offset-0 placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 md:text-sm"
        />

        {/* Bottom toolbar */}
        <div className="flex items-center justify-end gap-1.5 px-2 pb-2 pt-1">
          <ModelSelector model={model} onModelChange={onModelChange} disabled={disabled} />
          <Button
            type="submit"
            size="icon"
            variant="ghost"
            disabled={!canSend}
            className="h-7 w-7 rounded-lg shrink-0"
            aria-label="Send message"
          >
            <Send className="w-3.5 h-3.5" />
          </Button>
        </div>
      </form>
    </div>
  );
}
