'use client';

import { Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { DiffView } from './diff-view';

interface AiSuggestionDiffProps {
  draftContent: string;
  suggestedContent: string;
  isBusy?: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

/**
 * In-tab banner + diff shown when the AI chatbot has returned a proposed
 * prompt. Clicking **Accept** writes the suggestion into the draft via the
 * owning component (PromptTab), which triggers the existing autosave.
 */
export function AiSuggestionDiff({
  draftContent,
  suggestedContent,
  isBusy,
  onAccept,
  onDecline,
}: AiSuggestionDiffProps) {
  return (
    <div className="flex-1 flex flex-col min-h-0 gap-3">
      <div className="flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-blue-400 shrink-0" />
          <span className="text-foreground">AI suggested an update</span>
          <span className="text-muted-foreground">— review the changes below</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button size="sm" variant="outline" onClick={onDecline} disabled={isBusy}>
            Decline
          </Button>
          <Button size="sm" onClick={onAccept} disabled={isBusy}>
            Accept
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <DiffView fromContent={draftContent} toContent={suggestedContent} />
      </div>
    </div>
  );
}
