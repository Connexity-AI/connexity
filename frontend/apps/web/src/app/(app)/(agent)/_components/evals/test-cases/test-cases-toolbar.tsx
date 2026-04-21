'use client';

import { PenLine, Plus, Sparkles, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';

interface TestCasesToolbarProps {
  selectedCount: number;
  filteredCount: number;
  totalCount: number;
  onClearSelection: () => void;
  onBatchDelete: () => void;
  onAddManually: () => void;
  onAddWithAi: () => void;
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
}: Omit<TestCasesToolbarProps, 'onAddManually' | 'onAddWithAi'>) {
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
  onAddManually,
  onAddWithAi,
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
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 gap-1.5 text-xs"
          >
            <Plus className="h-3 w-3" />
            Add test case
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onSelect={onAddManually} className="gap-2">
            <PenLine className="h-3.5 w-3.5" />
            <div className="flex min-w-0 flex-col">
              <span className="text-sm">Manually</span>
              <span className="text-[11px] text-muted-foreground">
                Create a test case from scratch
              </span>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onAddWithAi} className="gap-2">
            <Sparkles className="h-3.5 w-3.5 text-violet-400" />
            <div className="flex min-w-0 flex-col">
              <span className="text-sm text-violet-300">With AI</span>
              <span className="text-[11px] text-muted-foreground">
                Describe what to cover, AI builds it
              </span>
            </div>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
