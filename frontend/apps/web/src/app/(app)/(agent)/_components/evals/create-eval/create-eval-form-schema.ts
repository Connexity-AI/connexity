import { z } from 'zod';

import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  splitDefaultLlmRouting,
} from '@/utils/split-default-llm-routing';

import type { EvalConfigCreate, JudgeConfig } from '@/client/types.gen';

export const DEFAULT_METRICS_PASS_THRESHOLD = 80;
export const DEFAULT_CASES_PASS_THRESHOLD = 100;

export function readJudgeMetricsThreshold(judge: JudgeConfig | null | undefined): number {
  return judge?.pass_threshold ?? DEFAULT_METRICS_PASS_THRESHOLD;
}

export function readJudgeCasesThreshold(judge: JudgeConfig | null | undefined): number {
  return judge?.cases_pass_threshold ?? DEFAULT_CASES_PASS_THRESHOLD;
}

export const createEvalFormSchema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(255),
  run: z.object({
    concurrency: z.number().int().min(1).max(50),
    max_turns: z.number().int().min(1).max(200).nullable(),
    tool_mode: z.enum(['mock', 'live']),
  }),
  test_cases: z
    .array(
      z.object({
        test_case_id: z.string().uuid(),
        name: z.string(),
        difficulty: z.string().nullable(),
        tags: z.array(z.string()),
        repetitions: z.number().int().min(1).max(100),
      })
    )
    .min(1, 'Add at least one test case'),
  judge: z.object({
    provider: z.string().min(1),
    model: z.string().min(1),
    metrics: z
      .array(
        z.object({
          metric: z.string(),
          enabled: z.boolean(),
          weight: z.number().min(0).max(10),
        })
      )
      .refine((ms) => ms.some((m) => m.enabled), 'Enable at least one metric'),
  }),
  thresholds: z.object({
    metrics_pass_threshold: z.number().int().min(0).max(100),
    cases_pass_threshold: z.number().int().min(0).max(100),
  }),
  persona: z.object({
    provider: z.string().min(1),
    model: z.string().min(1),
    temperature: z.number().min(0).max(2),
  }),
});

export type CreateEvalFormValues = z.infer<typeof createEvalFormSchema>;
export type CreateEvalTestCaseValue = CreateEvalFormValues['test_cases'][number];
export type CreateEvalMetricValue = CreateEvalFormValues['judge']['metrics'][number];

export function buildDefaults(
  name: string,
  defaultLlmRoute: string = BOOTSTRAP_DEFAULT_LLM_ROUTE
): CreateEvalFormValues {
  const { provider, model } = splitDefaultLlmRouting(defaultLlmRoute);
  return {
    name,
    run: {
      concurrency: 10,
      max_turns: 30,
      tool_mode: 'mock',
    },
    test_cases: [],
    judge: {
      provider,
      model,
      metrics: [],
    },
    thresholds: {
      metrics_pass_threshold: DEFAULT_METRICS_PASS_THRESHOLD,
      cases_pass_threshold: DEFAULT_CASES_PASS_THRESHOLD,
    },
    persona: {
      provider,
      model,
      temperature: 0.7,
    },
  };
}

export function formValuesToCreatePayload(
  values: CreateEvalFormValues,
  agentId: string
): EvalConfigCreate {
  const judge = {
    provider: values.judge.provider,
    model: values.judge.model,
    metrics: values.judge.metrics
      .filter((m) => m.enabled)
      .map((m) => ({ metric: m.metric, weight: m.weight })),
    pass_threshold: values.thresholds.metrics_pass_threshold,
    cases_pass_threshold: values.thresholds.cases_pass_threshold,
  };

  return {
    name: values.name,
    agent_id: agentId,
    config: {
      concurrency: values.run.concurrency,
      max_turns: values.run.max_turns,
      tool_mode: values.run.tool_mode,
      judge,
      user_simulator: {
        provider: values.persona.provider,
        model: values.persona.model,
        temperature: values.persona.temperature,
      },
    },
    members: values.test_cases.map((tc) => ({
      test_case_id: tc.test_case_id,
      repetitions: tc.repetitions,
    })),
  };
}
