'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';

interface EvalRunsColumnHeadersProps {
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: (checked: boolean) => void;
}

export function EvalRunsColumnHeaders({
  allSelected,
  someSelected,
  onToggleAll,
}: EvalRunsColumnHeadersProps) {
  return (
    <div className="sticky top-0 z-10 grid grid-cols-[32px_1fr_72px_110px_110px_96px] items-center gap-3 border-b border-border bg-background px-5 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
      <div className="flex items-center justify-start">
        <Checkbox
          aria-label="Select all runs"
          checked={allSelected ? true : someSelected ? 'indeterminate' : false}
          onCheckedChange={(value) => onToggleAll(value === true)}
        />
      </div>
      <span>Run</span>
      <span>Tool Calls</span>
      <span>Score</span>
      <span>Cases</span>
      <span aria-hidden="true" />
    </div>
  );
}
