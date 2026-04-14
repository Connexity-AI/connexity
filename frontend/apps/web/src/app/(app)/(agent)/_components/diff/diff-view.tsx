'use client';

import { useMemo } from 'react';

import { diffLines } from 'diff';
import { Check } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

interface DiffViewProps {
  fromContent: string;
  toContent: string;
}

type DiffLine = {
  text: string;
  type: 'added' | 'removed' | 'unchanged';
};

export function DiffView({ fromContent, toContent }: DiffViewProps) {
  const lines = useMemo<DiffLine[]>(() => {
    const changes = diffLines(fromContent, toContent);
    const result: DiffLine[] = [];

    for (const part of changes) {
      const raw = part.value.endsWith('\n') ? part.value.slice(0, -1) : part.value;

      const type: DiffLine['type'] = part.added ? 'added' : part.removed ? 'removed' : 'unchanged';

      for (const line of raw.split('\n')) {
        result.push({ text: line, type });
      }
    }
    return result;
  }, [fromContent, toContent]);

  const addedCount = lines.filter((line) => line.type === 'added').length;
  const removedCount = lines.filter((line) => line.type === 'removed').length;
  const hasChanges = addedCount > 0 || removedCount > 0;

  if (!hasChanges) {
    return (
      <div className="flex items-center justify-center border rounded-md bg-muted/20 py-10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="h-4 w-4 text-green-500" />
          No differences
        </div>
      </div>
    );
  }

  // NOTE: no internal ScrollArea here. The parent in <PromptTab /> is the
  // actual scroll container — keeping the scroll there is what lets the
  // sticky <DiffControls /> bar work (it needs a scrolling *ancestor*).
  return (
    <div className="flex flex-col border rounded-md overflow-hidden">
      <div className="flex items-center gap-3 px-3 py-2 border-b bg-muted/30 text-xs">
        <span className="text-green-600 dark:text-green-400 font-medium">+{addedCount}</span>
        <span className="text-red-600 dark:text-red-400 font-medium">-{removedCount}</span>
        <span className="text-muted-foreground">{lines.length} lines</span>
      </div>
      <div className="font-mono text-xs">
        {lines.map((line, index) => (
          <div
            key={index}
            className={cn(
              'flex items-start px-2 py-0.5',
              line.type === 'added' && 'bg-green-500/10 text-green-700 dark:text-green-300',
              line.type === 'removed' && 'bg-red-500/10 text-red-700 dark:text-red-300',
              line.type === 'unchanged' && 'text-muted-foreground'
            )}
          >
            <span
              className={cn(
                'w-6 shrink-0 select-none text-center',
                line.type === 'added' && 'text-green-600 dark:text-green-400',
                line.type === 'removed' && 'text-red-600 dark:text-red-400'
              )}
            >
              {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
            </span>
            <span className="whitespace-pre-wrap break-all flex-1">{line.text || ' '}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
