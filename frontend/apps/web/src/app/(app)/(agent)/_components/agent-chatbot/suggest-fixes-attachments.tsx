'use client';

import { Sparkles, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import {
  useSuggestFixes,
  type SuggestFixesCaseSummary,
} from '@/app/(app)/(agent)/_context/suggest-fixes-context';

export function SuggestFixesAttachments() {
  const { attachment, removeCase, clear } = useSuggestFixes();

  if (!attachment || attachment.caseSummaries.length === 0) return null;

  return (
    <div className="shrink-0 border-t border-border bg-accent/10 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs text-foreground">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          <span>
            <span className="tabular-nums">{attachment.caseSummaries.length}</span> attached test{' '}
            {attachment.caseSummaries.length === 1 ? 'case' : 'cases'}
          </span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={clear}
          className="h-auto px-1 py-0 text-xs font-normal text-muted-foreground/60 hover:bg-transparent hover:text-muted-foreground"
        >
          Clear
        </Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {attachment.caseSummaries.map((summary) => (
          <CaseChip
            key={summary.testCaseResultId}
            summary={summary}
            onRemove={() => removeCase(summary.testCaseResultId)}
          />
        ))}
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground/70">
        Send a message to analyze these cases and suggest prompt improvements.
      </p>
    </div>
  );
}

function CaseChip({
  summary,
  onRemove,
}: {
  summary: SuggestFixesCaseSummary;
  onRemove: () => void;
}) {
  const scoreLabel =
    summary.overallScore === null ? null : `${Math.round(summary.overallScore)}/100`;

  return (
    <div
      className={cn(
        'inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-1 text-xs',
        summary.passed === false
          ? 'border-red-500/20 bg-red-500/5 text-foreground'
          : 'border-border bg-background text-foreground'
      )}
    >
      <span className="truncate" title={summary.testCaseName}>
        {summary.testCaseName}
      </span>

      {scoreLabel ? (
        <span className="font-mono tabular-nums text-[10px] text-muted-foreground">
          {scoreLabel}
        </span>
      ) : null}

      <Button
        type="button"
        variant="ghost"
        size="icon"
        icon={X}
        onClick={onRemove}
        aria-label={`Remove ${summary.testCaseName}`}
        className="-mr-0.5 h-4 w-4 rounded text-muted-foreground/60 hover:bg-accent hover:text-foreground [&_svg]:size-3"
      />
    </div>
  );
}
