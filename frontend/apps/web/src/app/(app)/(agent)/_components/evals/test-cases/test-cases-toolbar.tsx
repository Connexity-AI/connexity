'use client';

import { FlaskConical, PenLine, Plus, Sparkles, Trash2 } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@workspace/ui/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';

import { UrlGenerator } from '@/common/url-generator/url-generator';

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

interface AddTestCaseDropdownProps {
  onAddManually: () => void;
  onAddWithAi: () => void;
}

function AddTestCaseDropdown({ onAddManually, onAddWithAi }: AddTestCaseDropdownProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" size="sm" variant="outline" className="h-7 gap-1.5 text-xs">
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
  );
}

interface CreateEvalButtonProps {
  agentId: string;
  selectedIds: string[];
  filteredIds: string[];
}

function CreateEvalButton({ agentId, selectedIds, filteredIds }: CreateEvalButtonProps) {
  const targetIds = selectedIds.length > 0 ? selectedIds : filteredIds;

  if (targetIds.length === 0) {
    return (
      <Button size="sm" className="h-7 gap-1.5 text-xs" disabled>
        <FlaskConical className="h-3 w-3" />
        Create Eval (0)
      </Button>
    );
  }

  const href = `${UrlGenerator.agentEvalsCreate(agentId)}?ids=${targetIds.join(',')}`;

  return (
    <Button asChild size="sm" className="h-7 gap-1.5 text-xs">
      <Link href={href}>
        <FlaskConical className="h-3 w-3" />
        Create Eval ({targetIds.length})
      </Link>
    </Button>
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
  AddTestCaseDropdown,
  CreateEvalButton,
});
