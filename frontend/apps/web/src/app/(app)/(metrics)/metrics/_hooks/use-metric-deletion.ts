'use client';

import { useState } from 'react';

import type { useDeleteCustomMetric } from '@/app/(app)/(metrics)/_hooks/use-custom-metrics';
import type { MetricRecord } from '../_components/metric-types';

type UseMetricDeletionArgs = {
  rows: MetricRecord[];
  deleteMutation: ReturnType<typeof useDeleteCustomMetric>;
  onDeleted: (ids: string[]) => void;
};

export function useMetricDeletion({ rows, deleteMutation, onDeleted }: UseMetricDeletionArgs) {
  const [deleteTarget, setDeleteTarget] = useState<MetricRecord[] | null>(null);

  const requestDeleteOne = (metric: MetricRecord) => setDeleteTarget([metric]);

  const requestDeleteMany = (ids: Set<string>) => {
    const targets = rows.filter((m) => ids.has(m.id));
    if (targets.length > 0) setDeleteTarget(targets);
  };

  const cancel = () => setDeleteTarget(null);

  const confirm = async () => {
    if (!deleteTarget) return;

    const ids = deleteTarget.map((m) => m.id);

    await Promise.all(ids.map((id) => deleteMutation.mutateAsync(id).catch(() => null)));

    onDeleted(ids);
    setDeleteTarget(null);
  };

  return {
    deleteTarget,
    requestDeleteOne,
    requestDeleteMany,
    cancel,
    confirm,
    isPending: deleteMutation.isPending,
  };
}
