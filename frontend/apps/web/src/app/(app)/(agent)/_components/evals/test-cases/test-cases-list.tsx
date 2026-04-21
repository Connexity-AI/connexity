'use client';

import { Button } from '@workspace/ui/components/ui/button';

import { GroupedTestCasesTable } from '@/app/(app)/(agent)/_components/evals/test-cases/grouped-test-cases-table';
import { DataTable } from '@/components/common/data-table/data-table';

import type { TestCasesTagGroup } from '@/app/(app)/(agent)/_components/evals/test-cases/grouped-test-cases-table';
import type { TestCasePublic } from '@/client/types.gen';
import type { ColumnDef } from '@tanstack/react-table';

interface TestCasesListProps {
  groupByTags: boolean;
  columns: ColumnDef<TestCasePublic>[];
  filtered: TestCasePublic[];
  tagGroups: TestCasesTagGroup[];
  collapsedGroups: Set<string>;
  selectedIds: Set<string>;
  onToggleGroup: (tag: string) => void;
  onToggleRow: (id: string, checked: boolean) => void;
  onOpenRow: (testCase: TestCasePublic) => void;
  onClearFilters: () => void;
}

function EmptyState({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <p className="text-sm text-muted-foreground">No test cases match the current filters</p>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClearFilters}
        className="h-7 px-2 text-xs text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground"
      >
        Clear all filters
      </Button>
    </div>
  );
}

export function TestCasesList({
  groupByTags,
  columns,
  filtered,
  tagGroups,
  collapsedGroups,
  selectedIds,
  onToggleGroup,
  onToggleRow,
  onOpenRow,
  onClearFilters,
}: TestCasesListProps) {
  if (groupByTags) {
    return (
      <GroupedTestCasesTable
        columns={columns}
        groups={tagGroups}
        collapsedGroups={collapsedGroups}
        onToggleGroup={onToggleGroup}
        selectedIds={selectedIds}
        onToggleRow={onToggleRow}
        onOpenRow={onOpenRow}
      />
    );
  }

  return (
    <DataTable
      columns={columns}
      data={filtered}
      onRowClick={onOpenRow}
      emptyState={<EmptyState onClearFilters={onClearFilters} />}
    />
  );
}
