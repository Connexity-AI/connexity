'use client';

import { useEffect, useState } from 'react';

import { Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { EditableDiffView } from './editable-diff-view';

interface AiSuggestionDiffProps {
  agentId: string;
  draftContent: string;
  suggestedContent: string;
  isBusy?: boolean;
  onAccept: (editedValue: string) => void;
  onDecline: () => void;
}

/**
 * In-tab banner + diff shown when the AI chatbot has returned a proposed
 * prompt. The right side is editable so the user can tweak the AI's
 * suggestion inline before clicking **Accept** — Accept then writes whatever
 * is currently in the buffer (not the pristine AI output) into the draft via
 * the owning component.
 */
export function AiSuggestionDiff({
  agentId,
  draftContent,
  suggestedContent,
  isBusy,
  onAccept,
  onDecline,
}: AiSuggestionDiffProps) {
  const [editedValue, setEditedValue] = useState(suggestedContent);

  // Reset the local buffer whenever the AI returns a new suggestion (new
  // chat turn) so the editor starts from the fresh proposal.
  useEffect(() => {
    setEditedValue(suggestedContent);
  }, [suggestedContent]);

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
          <Button size="sm" onClick={() => onAccept(editedValue)} disabled={isBusy}>
            Accept
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col">
        <EditableDiffView
          agentId={agentId}
          fromContent={draftContent}
          toContent={editedValue}
          editable
          onModifiedChange={setEditedValue}
        />
      </div>
    </div>
  );
}
