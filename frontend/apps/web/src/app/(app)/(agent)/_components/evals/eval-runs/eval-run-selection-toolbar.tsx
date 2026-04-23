'use client';

import { Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { SelectionCheckbox } from './selection-checkbox';

interface EvalRunSelectionToolbarProps {
  selectedCount: number;
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: (checked: boolean) => void;
  onSuggestFixes: () => void;
  onClear: () => void;
  disabled?: boolean;
}

export function EvalRunSelectionToolbar({
  selectedCount,
  allSelected,
  someSelected,
  onToggleAll,
  onSuggestFixes,
  onClear,
  disabled,
}: EvalRunSelectionToolbarProps) {
  // Radix Checkbox accepts 'indeterminate' as a CheckedState value, so we
  // don't need a ref + effect to toggle an HTMLInputElement.indeterminate.
  const checkedState: boolean | 'indeterminate' = someSelected ? 'indeterminate' : allSelected;

  return (
    <div className="flex h-10 shrink-0 items-center gap-4 border-b border-border px-5 py-2">
      <SelectionCheckbox
        checked={checkedState}
        onCheckedChange={(checked) => onToggleAll(checked === true)}
        aria-label="Select all"
      />

      <div className="flex items-center gap-3">
        <span className="text-xs text-foreground">
          <span className="tabular-nums">{selectedCount}</span> selected
        </span>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onSuggestFixes}
          disabled={disabled || selectedCount === 0}
          className="h-7 gap-1.5 px-2.5 text-xs font-normal text-muted-foreground hover:border-foreground/20 hover:bg-accent/50 hover:text-foreground"
        >
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          Suggest Fixes
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="h-auto px-1 py-0 text-xs font-normal text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground"
        >
          Clear
        </Button>
      </div>
    </div>
  );
}
