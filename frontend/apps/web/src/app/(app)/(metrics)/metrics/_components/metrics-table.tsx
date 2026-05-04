'use client';

import { BarChart3 } from 'lucide-react';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';

import { MetricRow } from './metric-row';

import type { MetricRecord } from './metric-types';

type MetricsTableProps = {
  rows: MetricRecord[];

  filtered: MetricRecord[];

  selectAllState: boolean | 'indeterminate';
  onToggleAll: (checked: boolean) => void;
  checkedIds: Set<string>;
  onCheck: (id: string, checked: boolean) => void;

  selectedId: string | null;
  onSelect: (id: string) => void;
  onToggleActive: (id: string, active: boolean) => void;
};

// Five-column grid: header row + scrollable body.
// `grid-cols-[32px_2fr_1fr_1fr_72px]` is mirrored by `MetricRow`
// so the header labels stay aligned to the row cells.
export function MetricsTable({
  rows,
  filtered,
  selectAllState,
  onToggleAll,
  checkedIds,
  onCheck,
  selectedId,
  onSelect,
  onToggleActive,
}: MetricsTableProps) {
  const allChecked = selectAllState === true;

  return (
    <>
      <div className="grid grid-cols-[32px_2fr_1fr_1fr_72px] border-b border-border shrink-0 px-5 items-center">
        <div className="py-2 flex items-center">
          <Checkbox
            checked={selectAllState}
            onCheckedChange={(c) => onToggleAll(c === true)}
            title={allChecked ? 'Deselect all' : 'Select all'}
          />
        </div>
        <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
          Name
        </div>
        <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
          Tier
        </div>
        <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
          Score type
        </div>
        <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
          Active
        </div>
      </div>

      {/* Body — empty state OR mapped rows */}
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground/40">
            <BarChart3 className="w-8 h-8" />
            <p className="text-sm">
              {rows.length === 0
                ? 'No metrics yet — create your first one.'
                : 'No metrics match the current filters'}
            </p>
          </div>
        ) : (
          filtered.map((m) => (
            <MetricRow
              key={m.id}
              metric={m}
              isSelected={selectedId === m.id}
              isChecked={checkedIds.has(m.id)}
              onSelect={onSelect}
              onCheck={onCheck}
              onToggleActive={onToggleActive}
            />
          ))
        )}
      </div>
    </>
  );
}
