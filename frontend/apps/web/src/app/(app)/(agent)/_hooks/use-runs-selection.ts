'use client';

import { useMemo, useState } from 'react';

export function useRunsSelection(visibleIds: string[]) {
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  const { allSelected, someSelected } = useMemo(() => {
    const all = visibleIds.length > 0 && visibleIds.every((id) => checkedIds.has(id));
    const some = !all && visibleIds.some((id) => checkedIds.has(id));
    return { allSelected: all, someSelected: some };
  }, [visibleIds, checkedIds]);

  const toggleAll = (checked: boolean) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        for (const id of visibleIds) next.add(id);
      } else {
        for (const id of visibleIds) next.delete(id);
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

  const clearSelection = () => setCheckedIds(new Set());

  return {
    checkedIds,
    allSelected,
    someSelected,
    toggleAll,
    toggleOne,
    clearSelection,
  };
}
