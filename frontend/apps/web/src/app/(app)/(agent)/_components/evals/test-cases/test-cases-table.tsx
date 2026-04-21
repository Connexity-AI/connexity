'use client';

import { useState } from 'react';

import { AddTestCaseAiDrawer } from '@/app/(app)/(agent)/_components/evals/test-cases/add-test-case-ai-drawer';
import { AddTestCaseManualDrawer } from '@/app/(app)/(agent)/_components/evals/test-cases/add-test-case-manual-drawer';
import { DeleteTestCasesDialog } from '@/app/(app)/(agent)/_components/evals/test-cases/delete-test-cases-dialog';
import { getTestCasesColumns } from '@/app/(app)/(agent)/_components/evals/test-cases/get-test-cases-columns';
import { TestCaseDetailDrawer } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-detail-drawer';
import { TestCasesFilterBar } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-filter-bar';
import { TestCasesList } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-list';
import { TestCasesToolbar } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-toolbar';
import { useTestCaseDrawer } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-case-drawer';
import { useTestCasesDeletion } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-cases-deletion';
import { useTestCasesFilters } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-cases-filters';
import { useTestCasesGrouping } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-cases-grouping';
import { useTestCasesSelection } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-cases-selection';

import type { TestCasePublic } from '@/client/types.gen';

interface TestCasesTableProps {
  agentId: string;
  testCases: TestCasePublic[];
}

export function TestCasesTable({ agentId, testCases }: TestCasesTableProps) {
  const { statusFilter, difficultyFilter, setFilters, filtered, clearFilters } =
    useTestCasesFilters(testCases);

  const filteredIds = filtered.map((item) => item.id);

  const selection = useTestCasesSelection(filteredIds);
  const drawer = useTestCaseDrawer();
  const grouping = useTestCasesGrouping(filtered);
  const [manualAddOpen, setManualAddOpen] = useState(false);
  const [aiAddOpen, setAiAddOpen] = useState(false);

  const deletion = useTestCasesDeletion({
    agentId,
    onDeleted: (ids) => {
      selection.removeIds(ids);
      if (drawer.activeTestCase && ids.includes(drawer.activeTestCase.id)) {
        drawer.close();
      }
    },
  });

  const columns = getTestCasesColumns({
    selectedIds: selection.selectedIds,
    allSelected: selection.allSelected,
    someSelected: selection.someSelected,
    onToggleRow: selection.toggleRow,
    onToggleAll: selection.toggleAll,
  });

  const requestBatchDelete = () => {
    deletion.requestBatch(testCases.filter((item) => selection.selectedIds.has(item.id)));
  };

  return (
    <>
      <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
        <TestCasesToolbar
          selectedCount={selection.selectedIds.size}
          filteredCount={filtered.length}
          totalCount={testCases.length}
          onClearSelection={selection.clear}
          onBatchDelete={requestBatchDelete}
          onAddManually={() => setManualAddOpen(true)}
          onAddWithAi={() => setAiAddOpen(true)}
        />

        <TestCasesFilterBar
          statusFilter={statusFilter}
          difficultyFilter={difficultyFilter}
          onStatusChange={(value) => setFilters({ status: value })}
          onDifficultyChange={(value) => setFilters({ difficulty: value })}
          groupByTags={grouping.groupByTags}
          onToggleGroupByTags={grouping.toggle}
        />

        <div className="flex-1 overflow-auto">
          <TestCasesList
            groupByTags={grouping.groupByTags}
            columns={columns}
            filtered={filtered}
            tagGroups={grouping.tagGroups}
            collapsedGroups={grouping.collapsedGroups}
            selectedIds={selection.selectedIds}
            onToggleGroup={grouping.toggleGroup}
            onToggleRow={selection.toggleRow}
            onOpenRow={drawer.openFor}
            onClearFilters={clearFilters}
          />
        </div>
      </div>

      <TestCaseDetailDrawer
        agentId={agentId}
        testCase={drawer.activeTestCase}
        open={drawer.open}
        onOpenChange={drawer.onOpenChange}
        onRequestDelete={deletion.requestSingle}
      />

      <DeleteTestCasesDialog
        open={deletion.dialogOpen}
        onOpenChange={deletion.onOpenChange}
        testCases={deletion.targets}
        onConfirm={deletion.confirm}
        isPending={deletion.isPending}
      />

      <AddTestCaseManualDrawer
        agentId={agentId}
        open={manualAddOpen}
        onOpenChange={setManualAddOpen}
      />

      <AddTestCaseAiDrawer agentId={agentId} open={aiAddOpen} onOpenChange={setAiAddOpen} />
    </>
  );
}
