'use client';

import { useEffect, useMemo, useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import { useFormContext } from 'react-hook-form';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import { useTestEvaluationEngine } from '@/app/(app)/(agent)/_hooks/use-test-evaluation-engine';
import { evaluationEnginesQuery } from '@/app/(app)/(agent)/_queries/evaluation-engines-query';
import { engineConfigForKind } from '@/app/(app)/(agent)/_utils/evaluation-engine-field-helpers';
import { EvaluationEngineKind } from '@/client/types.gen';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { EvaluationEngineKind as EvaluationEngineKindType } from '@/client/types.gen';

interface UseEvaluationEngineFieldArgs {
  agentId: string;
  defaultToBackendOption: boolean;
}

export function useEvaluationEngineField({
  agentId,
  defaultToBackendOption,
}: UseEvaluationEngineFieldArgs) {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const { data, isLoading, error } = useQuery(evaluationEnginesQuery(agentId));
  const [defaultApplied, setDefaultApplied] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const testEvaluationEngine = useTestEvaluationEngine();

  const selectedEngine = form.watch('run.evaluation_engine');
  const engineOptions = useMemo(() => data?.data ?? [], [data?.data]);
  const selectedKind = selectedEngine.kind;
  const customUrl =
    selectedEngine.kind === EvaluationEngineKind.CUSTOM_URL ? selectedEngine.url : '';

  useEffect(() => {
    if (engineOptions.length === 0) {
      return;
    }

    const selectedAvailable = engineOptions.some((option) => option.kind === selectedKind);
    if (selectedAvailable) {
      return;
    }

    const fallback = engineOptions.find((option) => option.is_default) ?? engineOptions[0];
    if (!fallback) {
      return;
    }

    form.setValue('run.evaluation_engine', engineConfigForKind(fallback.kind), {
      shouldDirty: true,
      shouldValidate: true,
    });
  }, [engineOptions, form, selectedKind]);

  useEffect(() => {
    if (defaultApplied || !defaultToBackendOption || engineOptions.length === 0) {
      return;
    }

    const defaultOption = engineOptions.find((option) => option.is_default) ?? engineOptions[0];
    if (!defaultOption) {
      return;
    }

    if (selectedKind === EvaluationEngineKind.CONNEXITY && defaultOption.kind !== selectedKind) {
      form.setValue('run.evaluation_engine', engineConfigForKind(defaultOption.kind), {
        shouldDirty: false,
        shouldValidate: true,
      });
    }

    setDefaultApplied(true);
  }, [defaultApplied, defaultToBackendOption, engineOptions, form, selectedKind]);

  const selectEngine = (kind: EvaluationEngineKindType) => {
    if (readOnly) {
      return;
    }

    const nextUrl = kind === EvaluationEngineKind.CUSTOM_URL ? customUrl : '';
    form.setValue('run.evaluation_engine', engineConfigForKind(kind, nextUrl), {
      shouldDirty: true,
      shouldValidate: true,
    });
    form.setValue('run.evaluation_engine_test', { ok: false, url: null }, {
      shouldDirty: true,
      shouldValidate: true,
    });
    setTestResult(null);
  };

  const setCustomUrl = (url: string) => {
    form.setValue('run.evaluation_engine', { kind: EvaluationEngineKind.CUSTOM_URL, url }, {
      shouldDirty: true,
      shouldValidate: true,
    });
    form.setValue('run.evaluation_engine_test', { ok: false, url: null }, {
      shouldDirty: true,
      shouldValidate: true,
    });
    setTestResult(null);
  };

  const testCustomUrl = async () => {
    const url = customUrl.trim();
    try {
      const result = await testEvaluationEngine.mutateAsync({
        agent_id: agentId,
        evaluation_engine: { kind: EvaluationEngineKind.CUSTOM_URL, url },
      });
      setTestResult(result);
      form.setValue('run.evaluation_engine_test', { ok: result.ok, url: result.ok ? url : null }, {
        shouldDirty: true,
        shouldValidate: true,
      });
      if (result.ok) {
        form.setValue('run.evaluation_engine', { kind: EvaluationEngineKind.CUSTOM_URL, url }, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to test URL';
      setTestResult({ ok: false, message });
      form.setValue('run.evaluation_engine_test', { ok: false, url: null }, {
        shouldDirty: true,
        shouldValidate: true,
      });
    }
  };

  const testDisabled =
    readOnly ||
    testEvaluationEngine.isPending ||
    customUrl.trim().length === 0 ||
    (!customUrl.trim().startsWith('http://') && !customUrl.trim().startsWith('https://'));

  return {
    form,
    readOnly,
    error,
    isLoading,
    engineOptions,
    selectedEngine,
    customUrl,
    testResult,
    testEvaluationEngine,
    selectEngine,
    setCustomUrl,
    testCustomUrl,
    testDisabled,
  };
}
