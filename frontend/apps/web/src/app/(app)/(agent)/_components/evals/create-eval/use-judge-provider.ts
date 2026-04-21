'use client';
'use no memo';

import { useFormContext, useWatch } from 'react-hook-form';

import { DEFAULT_MODELS, PROVIDERS } from '@/app/(app)/(agent)/_constants/agent';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

export function useJudgeProvider() {
  const form = useFormContext<CreateEvalFormValues>();
  const provider = useWatch({ control: form.control, name: 'judge.provider' });
  const models = PROVIDERS.find((p) => p.group === provider)?.models ?? [];

  const onProviderChange = (next: string) => {
    form.setValue('judge.provider', next, { shouldDirty: true });
    const fallback = DEFAULT_MODELS[next] ?? '';
    form.setValue('judge.model', fallback, { shouldDirty: true });
  };

  return {
    providers: PROVIDERS,
    models,
    onProviderChange,
  };
}
