'use no memo';
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';

import {
  buildDefaults,
  createEvalFormSchema,
  formValuesToCreatePayload,
  readJudgeCasesThreshold,
  readJudgeMetricsThreshold,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import {
  buildMetricRows,
  buildTestCaseRows,
} from '@/app/(app)/(agent)/_components/evals/create-eval/use-create-eval-form-helpers';
import { useAvailableMetrics } from '@/app/(app)/(agent)/_hooks/use-available-metrics';
import { useCreateEvalConfig } from '@/app/(app)/(agent)/_hooks/use-create-eval-config';
import { useCreateRun } from '@/app/(app)/(agent)/_hooks/use-create-run';
import { useSuspenseTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';
import { appConfigQueries } from '@/app/(app)/(agent)/_queries/app-config-query';
import { BOOTSTRAP_DEFAULT_LLM_ROUTE } from '@/utils/split-default-llm-routing';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type {
  EvalConfigMemberPublic,
  EvalConfigPublic,
  MetricDefinition,
} from '@/client/types.gen';

interface UseCreateEvalFormArgs {
  agentId: string;
  initialName: string;
  initialTestCaseIds?: string[];
  initialConfig?: EvalConfigPublic;
  initialMembers?: EvalConfigMemberPublic[];
}

interface UseCreateEvalFormResult {
  form: ReturnType<typeof useForm<CreateEvalFormValues>>;
  metrics: MetricDefinition[];
  submitSave: () => void;
  submitSaveAndRun: () => void;
  isPending: boolean;
  submitError: string | null;
}

export function useCreateEvalForm({
  agentId,
  initialName,
  initialTestCaseIds,
  initialConfig,
  initialMembers,
}: UseCreateEvalFormArgs): UseCreateEvalFormResult {
  const router = useRouter();
  const { data: metricsData } = useAvailableMetrics();
  const metrics = [...metricsData.data].sort((a, b) => a.name.localeCompare(b.name));

  const { data: appConfig } = useQuery(appConfigQueries.root);

  const { data: testCasesData } = useSuspenseTestCases(agentId);
  const testCases = testCasesData.data;

  const routing = appConfig?.default_llm_model ?? BOOTSTRAP_DEFAULT_LLM_ROUTE;
  const base = buildDefaults(initialName, routing);
  const cfg = initialConfig?.config ?? null;

  const memberSpecs = initialMembers
    ? initialMembers.map((m) => ({
        test_case_id: m.test_case_id,
        repetitions: m.repetitions,
      }))
    : (initialTestCaseIds ?? []).map((id) => ({ test_case_id: id, repetitions: 1 }));

  const defaults: CreateEvalFormValues = {
    ...base,
    name: initialConfig?.name ?? base.name,
    run: {
      concurrency: cfg?.concurrency ?? base.run.concurrency,
      max_turns: cfg?.max_turns ?? base.run.max_turns,
      tool_mode: cfg?.tool_mode ?? base.run.tool_mode,
    },
    test_cases: buildTestCaseRows(testCases, memberSpecs),
    judge: {
      provider: cfg?.judge?.provider ?? base.judge.provider,
      model: cfg?.judge?.model ?? base.judge.model,
      metrics: buildMetricRows(metrics, cfg?.judge?.metrics ?? null),
    },
    thresholds: {
      metrics_pass_threshold: cfg?.judge
        ? readJudgeMetricsThreshold(cfg.judge)
        : base.thresholds.metrics_pass_threshold,
      cases_pass_threshold: cfg?.judge
        ? readJudgeCasesThreshold(cfg.judge)
        : base.thresholds.cases_pass_threshold,
    },
    persona: {
      provider: cfg?.user_simulator?.provider ?? base.persona.provider,
      model: cfg?.user_simulator?.model ?? base.persona.model,
      temperature: cfg?.user_simulator?.temperature ?? base.persona.temperature,
    },
  };

  const form = useForm<CreateEvalFormValues>({
    resolver: zodResolver(createEvalFormSchema),
    defaultValues: defaults,
    values: defaults,
    resetOptions: { keepDirtyValues: true },
    mode: 'onBlur',
  });

  const { mutateAsync: createConfig, isPending: isCreatingConfig } = useCreateEvalConfig(agentId);
  const { mutateAsync: createRun, isPending: isCreatingRun } = useCreateRun(agentId);

  const [submitError, setSubmitError] = useState<string | null>(null);

  const submit = async (alsoRun: boolean) => {
    setSubmitError(null);
    const valid = await form.trigger();

    if (!valid) return;
    const values = form.getValues();

    try {
      const created = await createConfig(formValuesToCreatePayload(values, agentId));

      if (alsoRun) {
        await createRun({
          body: { agent_id: agentId, eval_config_id: created.id },
          autoExecute: true,
        });

        router.push(UrlGenerator.agentEvalsRuns(agentId));
      } else {
        router.push(UrlGenerator.agentEvalsConfigs(agentId));
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to save eval config');
    }
  };

  return {
    form,
    metrics,
    submitSave: () => void submit(false),
    submitSaveAndRun: () => void submit(true),
    isPending: isCreatingConfig || isCreatingRun,
    submitError,
  };
}
