import { z } from 'zod';

import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  splitDefaultLlmRouting,
} from '@/utils/split-default-llm-routing';
import { EvaluationEngineKind } from '@/client/types.gen';

import type { EvalConfigCreate, RunConfigInput } from '@/client/types.gen';

export type CreateEvalEvaluationEngine = NonNullable<RunConfigInput['evaluation_engine']>;

const evaluationEngineSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal(EvaluationEngineKind.CONNEXITY) }),
  z.object({ kind: z.literal(EvaluationEngineKind.RETELL) }),
  z.object({
    kind: z.literal(EvaluationEngineKind.CUSTOM_URL),
    url: z
      .string()
      .trim()
      .min(1, 'Custom URL is required')
      .refine(
        (url) => url.startsWith('http://') || url.startsWith('https://'),
        'Custom URL must start with http:// or https://'
      ),
  }),
]);

export const createEvalFormSchema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(255),
  run: z.object({
    concurrency: z.number().int().min(1).max(50),
    max_turns: z.number().int().min(1).max(200).nullable(),
    tool_mode: z.enum(['mock', 'live']),
    evaluation_engine: evaluationEngineSchema,
    evaluation_engine_test: z.object({
      ok: z.boolean(),
      url: z.string().nullable(),
    }),
    metrics_pass_threshold: z.number().min(0).max(100),
    cases_pass_threshold: z.number().min(0).max(100),
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
  persona: z.object({
    provider: z.string().min(1),
    model: z.string().min(1),
    temperature: z.number().min(0).max(2),
  }),
}).superRefine((values, ctx) => {
  if (values.run.evaluation_engine.kind !== EvaluationEngineKind.CUSTOM_URL) {
    return;
  }

  const testedUrl = values.run.evaluation_engine_test.url;
  const currentUrl = values.run.evaluation_engine.url.trim();
  if (values.run.evaluation_engine_test.ok && testedUrl === currentUrl) {
    return;
  }

  ctx.addIssue({
    code: 'custom',
    path: ['run', 'evaluation_engine', 'url'],
    message: 'Test URL successfully before saving this eval config',
  });
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
      evaluation_engine: { kind: EvaluationEngineKind.CONNEXITY },
      evaluation_engine_test: { ok: false, url: null },
      metrics_pass_threshold: 80,
      cases_pass_threshold: 100,
    },
    test_cases: [],
    judge: {
      provider,
      model,
      metrics: [],
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
  const evaluationEngine = values.run.evaluation_engine;
  const toolMode =
    evaluationEngine.kind === EvaluationEngineKind.CONNEXITY ? values.run.tool_mode : 'mock';

  return {
    name: values.name,
    agent_id: agentId,
    config: {
      concurrency: values.run.concurrency,
      max_turns: values.run.max_turns,
      tool_mode: toolMode,
      evaluation_engine: evaluationEngine,
      metrics_pass_threshold: values.run.metrics_pass_threshold,
      cases_pass_threshold: values.run.cases_pass_threshold,
      judge: {
        provider: values.judge.provider,
        model: values.judge.model,
        metrics: values.judge.metrics
          .filter((m) => m.enabled)
          .map((m) => ({ metric: m.metric, weight: m.weight })),
      },
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
