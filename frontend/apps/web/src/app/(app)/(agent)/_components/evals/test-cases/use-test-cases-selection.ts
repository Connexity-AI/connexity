'use client';

import { useState } from 'react';

export function useTestCasesSelection(filteredIds: string[]) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const selectedInView = filteredIds.filter((id) => selectedIds.has(id));
  const allSelected = filteredIds.length > 0 && selectedInView.length === filteredIds.length;
  const someSelected = selectedInView.length > 0 && !allSelected;

  const toggleRow = (id: string, checked: boolean) => {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const toggleAll = (checked: boolean) => {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (checked) filteredIds.forEach((id) => next.add(id));
      else filteredIds.forEach((id) => next.delete(id));
      return next;
    });
  };

  const clear = () => setSelectedIds(new Set());

  const removeIds = (ids: string[]) => {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  return {
    selectedIds,
    allSelected,
    someSelected,
    toggleRow,
    toggleAll,
    clear,
    removeIds,
  };
}
