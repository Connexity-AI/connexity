'use client';

import { Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

type MetricsSummaryBarProps = {
  selectedCount: number;

  filteredCount: number;

  totalCount: number;
  onDeleteSelected: () => void;
  onClearSelection: () => void;
};

export function MetricsSummaryBar({
  selectedCount,
  filteredCount,
  totalCount,
  onDeleteSelected,
  onClearSelection,
}: MetricsSummaryBarProps) {
  return (
    <div className="flex items-center justify-between px-5 py-2 border-b border-border shrink-0">
      {selectedCount > 0 ? (
        <div className="flex items-center gap-3">
          <span className="text-xs text-foreground">
            <span className="tabular-nums">{selectedCount}</span> selected
          </span>
          <Button
            onClick={onDeleteSelected}
            variant="ghost"
            size="sm"
            className="flex items-center gap-1.5 h-auto p-0 text-xs text-red-400 hover:text-red-300 hover:bg-transparent transition-colors"
            type="button"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete selected
          </Button>
          <Button
            onClick={onClearSelection}
            variant="ghost"
            size="sm"
            className="h-auto p-0 text-xs text-muted-foreground/50 hover:text-muted-foreground hover:bg-transparent transition-colors"
            type="button"
          >
            Clear
          </Button>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {filteredCount}
          {filteredCount !== totalCount ? ` of ${totalCount}` : ''} metric
          {totalCount === 1 ? '' : 's'}
        </p>
      )}
    </div>
  );
}
