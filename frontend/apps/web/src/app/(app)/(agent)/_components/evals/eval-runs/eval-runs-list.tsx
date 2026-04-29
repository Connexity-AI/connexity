'use client';

import { useMemo } from 'react';

import { useEvalRunsDerivations } from '@/app/(app)/(agent)/_hooks/use-eval-runs-derivations';
import { useEvalRunsView } from '@/app/(app)/(agent)/_hooks/use-eval-runs-view';
import { useRunsSelection } from '@/app/(app)/(agent)/_hooks/use-runs-selection';

import { EvalRunsColumnHeaders } from './eval-runs-column-headers';
import { EvalRunsEmptyState } from './eval-runs-empty-state';
import { EvalRunsFilterBar } from './eval-runs-filter-bar';
import { EvalRunsListBody } from './eval-runs-list-body';
import { EvalRunsToolbar } from './eval-runs-toolbar';

import type { EvalConfigPublic, RunPublic } from '@/client/types.gen';

interface EvalRunsListProps {
  agentId: string;
  runs: RunPublic[];
  configs: EvalConfigPublic[];
  onOpenRun: (runId: string) => void;
}

export function EvalRunsList({ agentId, runs, configs, onOpenRun }: EvalRunsListProps) {
  const { configById, versions, latestVersion, repeatIndexByRun } =
    useEvalRunsDerivations({ runs, configs });

  const view = useEvalRunsView({ runs, configById });

  const visibleIds = useMemo(
    () => view.sortedRuns.map((r) => r.id),
    [view.sortedRuns]
  );
  const selection = useRunsSelection(visibleIds);

  if (runs.length === 0) {
    return <EvalRunsEmptyState agentId={agentId} />;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <EvalRunsToolbar
        agentId={agentId}
        totalCount={runs.length}
        filteredCount={view.sortedRuns.length}
        selectedIds={Array.from(selection.checkedIds)}
        onClearSelection={selection.clearSelection}
      />

      <EvalRunsFilterBar
        versions={versions}
        latestVersion={latestVersion}
        versionFilter={view.versionFilter}
        onVersionFilterChange={view.setVersionFilter}
        groupByConfig={view.groupByConfig}
        onGroupByConfigChange={view.setGroupByConfig}
      />

      <EvalRunsColumnHeaders
        allSelected={selection.allSelected}
        someSelected={selection.someSelected}
        onToggleAll={selection.toggleAll}
      />

      <div className="flex-1 overflow-auto">
        <EvalRunsListBody
          groupedRuns={view.groupedRuns}
          sortedRuns={view.sortedRuns}
          configById={configById}
          repeatIndexByRun={repeatIndexByRun}
          latestVersion={latestVersion}
          checkedIds={selection.checkedIds}
          onToggleOne={selection.toggleOne}
          onOpenRun={onOpenRun}
        />
      </div>
    </div>
  );
}
