'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import {
  buildDefaults,
  createEvalFormSchema,
  formValuesToCreatePayload,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import { useAvailableMetrics } from '@/app/(app)/(agent)/_hooks/use-available-metrics';
import { useCreateEvalConfig } from '@/app/(app)/(agent)/_hooks/use-create-eval-config';
import { useCreateRun } from '@/app/(app)/(agent)/_hooks/use-create-run';
import { useSuspenseTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';

import type {
  CreateEvalFormValues,
  CreateEvalTestCaseValue,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type {
  EvalConfigMemberPublic,
  EvalConfigPublic,
  MetricDefinition,
  TestCasePublic,
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

function buildMetricRows(
  metrics: MetricDefinition[],
  existing?: { metric: string; weight?: number | null }[] | null
) {
  if (existing && existing.length > 0) {
    const overrides = new Map(existing.map((m) => [m.metric, m.weight ?? null]));
    return metrics.map((def) => {
      const enabled = overrides.has(def.name);
      const overrideWeight = overrides.get(def.name);
      return {
        metric: def.name,
        enabled,
        weight: overrideWeight ?? def.default_weight,
      };
    });
  }
  return metrics.map((def) => ({
    metric: def.name,
    enabled: def.include_in_defaults !== false,
    weight: def.default_weight,
  }));
}

function buildTestCaseRows(
  testCases: TestCasePublic[],
  rowsSpec: { test_case_id: string; repetitions: number }[]
): CreateEvalTestCaseValue[] {
  const byId = new Map(testCases.map((tc) => [tc.id, tc]));
  const rows: CreateEvalTestCaseValue[] = [];
  for (const spec of rowsSpec) {
    const tc = byId.get(spec.test_case_id);
    if (!tc) continue;
    rows.push({
      test_case_id: tc.id,
      name: tc.name,
      difficulty: tc.difficulty ?? null,
      tags: tc.tags ?? [],
      repetitions: spec.repetitions,
    });
  }
  return rows;
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
  const metrics = metricsData.data;

  const { data: testCasesData } = useSuspenseTestCases(agentId);
  const testCases = testCasesData.data;

  const defaults = useMemo<CreateEvalFormValues>(() => {
    const base = buildDefaults(initialName);
    const cfg = initialConfig?.config ?? null;

    const memberSpecs = initialMembers
      ? initialMembers.map((m) => ({
          test_case_id: m.test_case_id,
          repetitions: m.repetitions,
        }))
      : (initialTestCaseIds ?? []).map((id) => ({ test_case_id: id, repetitions: 1 }));

    return {
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
      persona: {
        provider: cfg?.user_simulator?.provider ?? base.persona.provider,
        model: cfg?.user_simulator?.model ?? base.persona.model,
        temperature: cfg?.user_simulator?.temperature ?? base.persona.temperature,
      },
    };
  }, [initialName, initialConfig, initialMembers, initialTestCaseIds, metrics, testCases]);

  const form = useForm<CreateEvalFormValues>({
    resolver: zodResolver(createEvalFormSchema),
    defaultValues: defaults,
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
