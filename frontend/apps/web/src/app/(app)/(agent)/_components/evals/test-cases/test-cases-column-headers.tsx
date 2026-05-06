'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';

interface TestCasesColumnHeadersProps {
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: (checked: boolean) => void;
}

export function TestCasesColumnHeaders({
  allSelected,
  someSelected,
  onToggleAll,
}: TestCasesColumnHeadersProps) {
  return (
    <div className="grid shrink-0 grid-cols-[32px_minmax(0,1fr)_120px_minmax(0,1fr)] items-center gap-4 border-b border-border bg-background px-5 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
      <div className="flex items-center justify-start">
        <Checkbox
          aria-label="Select all test cases"
          checked={allSelected ? true : someSelected ? 'indeterminate' : false}
          onCheckedChange={(value) => onToggleAll(value === true)}
        />
      </div>

      <span>Name</span>

      <span>Difficulty</span>

      <span>Tags</span>
    </div>
  );
}
