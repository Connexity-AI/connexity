'use client';

import { useEffect } from 'react';

import type { UseFormReturn } from 'react-hook-form';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

/** When live tool execution becomes unavailable, reset tool_mode from live to mock. */
export function useToolModeLiveGuard(
  form: UseFormReturn<CreateEvalFormValues>,
  liveUnavailable: boolean
) {
  const toolMode = form.watch('run.tool_mode');

  useEffect(() => {
    if (liveUnavailable && toolMode === 'live') {
      form.setValue('run.tool_mode', 'mock', { shouldValidate: true, shouldDirty: true });
    }
  }, [liveUnavailable, toolMode, form]);
}
