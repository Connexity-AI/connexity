'use client';

import {
  useCreateCustomMetric,
  useCustomMetrics,
  useDeleteCustomMetric,
  useUpdateCustomMetric,
} from '@/app/(app)/(metrics)/_hooks/use-custom-metrics';
import { useMetricDeletion } from '../_hooks/use-metric-deletion';
import { useMetricDetailPanel } from '../_hooks/use-metric-detail-panel';
import { useMetricFilters } from '../_hooks/use-metric-filters';
import { useMetricSelection } from '../_hooks/use-metric-selection';
import { DeleteConfirmDialog } from './delete-confirm-dialog';
import { MetricDetailDrawer } from './metric-detail-drawer';
import { MetricsFilterPills } from './metrics-filter-pills';
import { MetricsSummaryBar } from './metrics-summary-bar';
import { MetricsTable } from './metrics-table';

export function MetricsPage() {
  const { data } = useCustomMetrics();
  const rows = data.data;

  const createMutation = useCreateCustomMetric();
  const updateMutation = useUpdateCustomMetric();
  const deleteMutation = useDeleteCustomMetric();

  const { tierFilter, setTierFilter, scoreFilter, setScoreFilter, filtered } =
    useMetricFilters(rows);

  const {
    checkedIds,
    selectAllState,
    toggleAll,
    toggleOne,
    clear: clearSelection,
    removeMany: removeFromSelection,
  } = useMetricSelection(filtered);

  const {
    selectedId,
    setSelectedId,
    selectedMetric,
    detailSource,
    savedFlash,
    selectMetric,
    closeDetail,
    handleSave,
  } = useMetricDetailPanel({ rows, createMutation, updateMutation });

  const {
    deleteTarget,
    requestDeleteOne,
    requestDeleteMany,
    cancel: cancelDelete,
    confirm: confirmDelete,
    isPending: isDeleting,
  } = useMetricDeletion({
    rows,
    deleteMutation,
    onDeleted: (ids) => {
      removeFromSelection(ids);
      if (selectedId && ids.includes(selectedId)) setSelectedId(null);
    },
  });

  // The "active" toggle is the inverse of the backing `is_draft` flag:
  // active rows are visible to eval configs; drafts are hidden.
  const handleToggleActive = (id: string, active: boolean) => {
    updateMutation.mutate({
      metricId: id,
      body: { is_draft: !active },
    });
  };

  return (
    <div className="flex h-full overflow-hidden bg-background">
      <div className="flex flex-col min-h-0 flex-1">
        <MetricsSummaryBar
          selectedCount={checkedIds.size}
          filteredCount={filtered.length}
          totalCount={rows.length}
          onDeleteSelected={() => requestDeleteMany(checkedIds)}
          onClearSelection={clearSelection}
        />

        <MetricsFilterPills
          tierFilter={tierFilter}
          onTierChange={setTierFilter}
          scoreFilter={scoreFilter}
          onScoreChange={setScoreFilter}
        />

        <MetricsTable
          rows={rows}
          filtered={filtered}
          selectAllState={selectAllState}
          onToggleAll={toggleAll}
          checkedIds={checkedIds}
          onCheck={toggleOne}
          selectedId={selectedId}
          onSelect={selectMetric}
          onToggleActive={handleToggleActive}
        />
      </div>

      <MetricDetailDrawer
        source={detailSource}
        saved={savedFlash}
        saving={createMutation.isPending || updateMutation.isPending}
        onSave={handleSave}
        onDelete={() => {
          if (selectedMetric) requestDeleteOne(selectedMetric);
        }}
        onClose={closeDetail}
      />

      <DeleteConfirmDialog
        items={deleteTarget}
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
        isPending={isDeleting}
      />
    </div>
  );
}
