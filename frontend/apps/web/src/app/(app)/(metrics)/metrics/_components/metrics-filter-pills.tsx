'use client';

import { FilterPill } from './filter-pill';
import { SCORE_FILTERS, SCORE_TYPE_META, TIER_FILTERS, TIER_META } from './metric-meta';

import type { ScoreFilter, TierFilter } from './metric-meta';

type MetricsFilterPillsProps = {
  tierFilter: TierFilter;
  onTierChange: (next: TierFilter) => void;
  scoreFilter: ScoreFilter;
  onScoreChange: (next: ScoreFilter) => void;
};

export function MetricsFilterPills({
  tierFilter,
  onTierChange,
  scoreFilter,
  onScoreChange,
}: MetricsFilterPillsProps) {
  return (
    <div className="flex items-center px-4 py-2 border-b border-border shrink-0 gap-2 flex-wrap">
      <div className="flex items-center gap-0.5 bg-accent/40 rounded-md p-0.5 shrink-0">
        {TIER_FILTERS.map((t) => (
          <FilterPill key={t} active={tierFilter === t} onClick={() => onTierChange(t)}>
            {t === 'all' ? 'All tiers' : TIER_META[t].label}
          </FilterPill>
        ))}
      </div>

      <div className="w-px h-4 bg-border shrink-0" />

      <div className="flex items-center gap-0.5 bg-accent/40 rounded-md p-0.5 shrink-0">
        {SCORE_FILTERS.map((s) => (
          <FilterPill key={s} active={scoreFilter === s} onClick={() => onScoreChange(s)}>
            {s === 'all' ? 'All types' : SCORE_TYPE_META[s].label}
          </FilterPill>
        ))}
      </div>
    </div>
  );
}
