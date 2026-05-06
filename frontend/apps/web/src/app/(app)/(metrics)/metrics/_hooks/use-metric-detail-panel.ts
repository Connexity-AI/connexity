'use client';

import { useMemo, useState } from 'react';

import { useQueryState } from 'nuqs';

import { MetricDetail, metricToDraft, newDraft } from '../_components/metric-detail';

import type {
  useCreateCustomMetric,
  useUpdateCustomMetric,
} from '@/app/(app)/(metrics)/_hooks/use-custom-metrics';
import type { MetricDraft } from '../_components/metric-detail';
import type { MetricRecord } from '../_components/metric-types';

type UseMetricDetailPanelArgs = {
  rows: MetricRecord[];
  createMutation: ReturnType<typeof useCreateCustomMetric>;
  updateMutation: ReturnType<typeof useUpdateCustomMetric>;
};

export function useMetricDetailPanel({
  rows,
  createMutation,
  updateMutation,
}: UseMetricDetailPanelArgs) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  // Draft-open state lives in the URL (`?new=1`). Drives the drawer
  // directly — no `useState` mirror, no syncing effect. The layout
  // header's "New metric" link sets the param; closing the drawer
  // clears it. Refresh / back-forward / deep links work for free.
  const [newParam, setNewParam] = useQueryState('new');
  const draftOpen = newParam === '1';

  const selectedMetric = useMemo(
    () => rows.find((m) => m.id === selectedId) ?? null,
    [rows, selectedId]
  );

  const detailSource: MetricDraft | null = draftOpen
    ? newDraft()
    : selectedMetric
      ? metricToDraft(selectedMetric)
      : null;

  const flashSaved = () => {
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 2000);
  };

  const selectMetric = (id: string) => {
    setNewParam(null);
    setSelectedId((cur) => (cur === id ? null : id));
  };

  const closeDetail = () => {
    setSelectedId(null);
    setNewParam(null);
  };

  const handleSave: React.ComponentProps<typeof MetricDetail>['onSave'] = (patch, draft) => {
    if (draft.id === null) {
      createMutation.mutate(
        {
          name: draft.name,
          display_name: draft.display_name,
          description: draft.description,
          tier: draft.tier,
          default_weight: draft.default_weight,
          score_type: draft.score_type,
          rubric: draft.rubric,

          include_in_defaults: draft.active,
          is_draft: !draft.active,
        },
        {
          onSuccess: () => {
            setNewParam(null);
            setSelectedId(null);
            flashSaved();
          },
        }
      );
    } else {
      updateMutation.mutate({ metricId: draft.id, body: patch }, { onSuccess: () => flashSaved() });
    }
  };

  return {
    selectedId,
    setSelectedId,
    selectedMetric,
    detailSource,
    savedFlash,
    selectMetric,
    closeDetail,
    handleSave,
  };
}
