'use client';
'use no memo';

import { useMemo } from 'react';

import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { MetricDefinition } from '@/client/types.gen';

type MetricRow = CreateEvalFormValues['judge']['metrics'][number];

interface UseJudgeMetricsArgs {
  metrics: MetricDefinition[];
}

export function useJudgeMetrics({ metrics }: UseJudgeMetricsArgs) {
  const form = useFormContext<CreateEvalFormValues>();
  const fieldArray = useFieldArray({ control: form.control, name: 'judge.metrics' });
  const watched = useWatch({ control: form.control, name: 'judge.metrics' }) ?? [];

  const byName = useMemo(() => {
    const map = new Map<string, MetricDefinition>();
    metrics.forEach((m) => map.set(m.name, m));
    return map;
  }, [metrics]);

  const enabledCount = watched.filter((m) => m.enabled).length;
  const allEnabled = watched.length > 0 && enabledCount === watched.length;

  const toggleAll = (next: boolean) => {
    fieldArray.replace(watched.map((m) => ({ ...m, enabled: next })));
  };

  const updateRow = (index: number, row: MetricRow) => {
    fieldArray.update(index, row);
  };

  const rootError = form.formState.errors.judge?.metrics?.message;

  return {
    fields: fieldArray.fields,
    rows: watched,
    byName,
    enabledCount,
    allEnabled,
    toggleAll,
    updateRow,
    rootError,
  };
}
