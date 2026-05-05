'use client';

import { useState } from 'react';

import type { MetricRecord } from '../_components/metric-types';

export function useMetricSelection(filtered: MetricRecord[]) {
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  const allChecked = filtered.length > 0 && filtered.every((m) => checkedIds.has(m.id));
  const someChecked = !allChecked && filtered.some((m) => checkedIds.has(m.id));

  const selectAllState: boolean | 'indeterminate' = someChecked ? 'indeterminate' : allChecked;

  const toggleAll = (checked: boolean) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        filtered.forEach((m) => next.add(m.id));
      } else {
        filtered.forEach((m) => next.delete(m.id));
      }
      return next;
    });
  };

  const toggleOne = (id: string, checked: boolean) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const clear = () => setCheckedIds(new Set());

  const removeMany = (ids: string[]) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  return {
    checkedIds,
    selectAllState,
    allChecked,
    toggleAll,
    toggleOne,
    clear,
    removeMany,
  };
}
