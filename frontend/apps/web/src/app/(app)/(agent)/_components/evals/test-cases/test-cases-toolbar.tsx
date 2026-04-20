'use client';

import { Plus, Sparkles, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface TestCasesToolbarProps {
  selectedCount: number;
  filteredCount: number;
  totalCount: number;
  onClearSelection: () => void;
  onBatchDelete: () => void;
  onGenerateClick: () => void;
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

function pluralSuffix(count: number) {
  if (count === 1) return '';
  return 's';
}

function CountLabel({ filteredCount, totalCount }: { filteredCount: number; totalCount: number }) {
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

function LeadingContent({
  selectedCount,
  filteredCount,
  totalCount,
  onBatchDelete,
  onClearSelection,
}: Omit<TestCasesToolbarProps, 'onGenerateClick'>) {
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

export function TestCasesToolbar({
  selectedCount,
  filteredCount,
  totalCount,
  onClearSelection,
  onBatchDelete,
  onGenerateClick,
}: TestCasesToolbarProps) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-2.5 h-12">
      <LeadingContent
        selectedCount={selectedCount}
        filteredCount={filteredCount}
        totalCount={totalCount}
        onBatchDelete={onBatchDelete}
        onClearSelection={onClearSelection}
      />
      {/* <div className="flex items-center gap-1.5">
        <Button size="sm" className="h-7 gap-1.5 text-xs" onClick={onGenerateClick}>
          <Sparkles className="h-3 w-3" />
          Generate
        </Button>
        <Button size="sm" variant="outline" className="h-7 gap-1.5 text-xs" disabled>
          <Plus className="h-3 w-3" />
          Add test case
        </Button>
      </div> */}
    </div>
  );
}
