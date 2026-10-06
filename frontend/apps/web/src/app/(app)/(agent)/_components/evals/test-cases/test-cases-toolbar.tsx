'use client';

import { Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import type { ReactNode } from 'react';

function pluralSuffix(count: number) {
  if (count === 1) return '';
  return 's';
}

function Root({ children }: { children: ReactNode }) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-2.5 h-12">
      {children}
    </div>
  );
}

function Actions({ children }: { children: ReactNode }) {
  return <div className="flex items-center gap-1.5">{children}</div>;
}

interface CountLabelProps {
  filteredCount: number;
  totalCount: number;
}

function CountLabel({ filteredCount, totalCount }: CountLabelProps) {
  if (filteredCount === totalCount) {
    return (
      <p className="text-xs text-muted-foreground">
        {filteredCount} test case{pluralSuffix(filteredCount)}
      </p>
    );
  }
  return (
    <p className="text-xs text-muted-foreground">
      {filteredCount} of {totalCount} test case{pluralSuffix(filteredCount)}
    </p>
  );
}

interface SelectionActionsProps {
  selectedCount: number;
  onBatchDelete: () => void;
  onClearSelection: () => void;
}

function SelectionActions({
  selectedCount,
  onBatchDelete,
  onClearSelection,
}: SelectionActionsProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-foreground">
        <span className="tabular-nums">{selectedCount}</span> selected
      </span>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onBatchDelete}
        className="h-7 gap-1.5 px-2 text-xs text-red-400 hover:bg-transparent hover:text-red-300"
      >
        <Trash2 className="h-3.5 w-3.5" />
        Delete selected
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClearSelection}
        className="h-7 px-2 text-xs text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground"
      >
        Clear
      </Button>
    </div>
  );
}

interface LeadingProps {
  selectedCount: number;
  filteredCount: number;
  totalCount: number;
  onBatchDelete: () => void;
  onClearSelection: () => void;
}

function Leading({
  selectedCount,
  filteredCount,
  totalCount,
  onBatchDelete,
  onClearSelection,
}: LeadingProps) {
  if (selectedCount > 0) {
    return (
      <SelectionActions
        selectedCount={selectedCount}
        onBatchDelete={onBatchDelete}
        onClearSelection={onClearSelection}
      />
    );
  }
  return <CountLabel filteredCount={filteredCount} totalCount={totalCount} />;
}

export const TestCasesToolbar = Object.assign(Root, {
  Leading,
  Actions,
});
