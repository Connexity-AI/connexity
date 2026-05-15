import { z } from 'zod';

import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  splitDefaultLlmRouting,
} from '@/utils/split-default-llm-routing';
import { TextRuntimeKind } from '@/client/types.gen';

import type { EvalConfigCreate, RunConfigInput } from '@/client/types.gen';

export type CreateEvalRuntime = NonNullable<RunConfigInput['runtime']>;

const runtimeSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal(TextRuntimeKind.CONNEXITY) }),
  z.object({ kind: z.literal(TextRuntimeKind.RETELL) }),
  z.object({
    kind: z.literal(TextRuntimeKind.CUSTOM_ENDPOINT),
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
    runtime: runtimeSchema,
    runtime_test: z.object({
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
  if (values.run.runtime.kind !== TextRuntimeKind.CUSTOM_ENDPOINT) {
    return;
  }

  const testedUrl = values.run.runtime_test.url;
  const currentUrl = values.run.runtime.url.trim();
  if (values.run.runtime_test.ok && testedUrl === currentUrl) {
    return;
  }

  ctx.addIssue({
    code: 'custom',
    path: ['run', 'runtime', 'url'],
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
      runtime: { kind: TextRuntimeKind.CONNEXITY },
      runtime_test: { ok: false, url: null },
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
  const runtime = values.run.runtime;
  const toolMode =
    runtime.kind === TextRuntimeKind.CONNEXITY ? values.run.tool_mode : 'mock';

  return {
    name: values.name,
    agent_id: agentId,
    config: {
      concurrency: values.run.concurrency,
      max_turns: values.run.max_turns,
      tool_mode: toolMode,
      mode: 'text',
      runtime,
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
