import { z } from 'zod';

import { DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER } from '@/constants/llm-models';

import type { EvalConfigCreate } from '@/client/types.gen';

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
  persona: z.object({
    provider: z.string().min(1),
    model: z.string().min(1),
    temperature: z.number().min(0).max(2),
  }),
});

export type CreateEvalFormValues = z.infer<typeof createEvalFormSchema>;
export type CreateEvalTestCaseValue = CreateEvalFormValues['test_cases'][number];
export type CreateEvalMetricValue = CreateEvalFormValues['judge']['metrics'][number];

export function buildDefaults(name: string): CreateEvalFormValues {
  return {
    name,
    run: {
      concurrency: 10,
      max_turns: 30,
      tool_mode: 'mock',
    },
    test_cases: [],
    judge: {
      provider: DEFAULT_LLM_PROVIDER,
      model: DEFAULT_LLM_MODEL,
      metrics: [],
    },
    persona: {
      provider: DEFAULT_LLM_PROVIDER,
      model: DEFAULT_LLM_MODEL,
      temperature: 0.7,
    },
  };
}

export function formValuesToCreatePayload(
  values: CreateEvalFormValues,
  agentId: string
): EvalConfigCreate {
  return {
    name: values.name,
    agent_id: agentId,
    config: {
      concurrency: values.run.concurrency,
      max_turns: values.run.max_turns,
      tool_mode: values.run.tool_mode,
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
