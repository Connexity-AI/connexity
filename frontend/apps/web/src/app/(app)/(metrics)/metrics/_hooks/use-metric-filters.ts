'use client';

import { useMemo, useState } from 'react';

import type { ScoreFilter, TierFilter } from '../_components/metric-meta';
import type { MetricRecord } from '../_components/metric-types';

export function useMetricFilters(rows: MetricRecord[]) {
  const [tierFilter, setTierFilter] = useState<TierFilter>('all');
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all');

  const filtered = useMemo(
    () =>
      rows.filter((m) => {
        if (tierFilter !== 'all' && m.tier !== tierFilter) return false;
        if (scoreFilter !== 'all' && m.score_type !== scoreFilter) return false;
        return true;
      }),
    [rows, tierFilter, scoreFilter]
  );

  return {
    tierFilter,
    setTierFilter,
    scoreFilter,
    setScoreFilter,
    filtered,
  };
}
