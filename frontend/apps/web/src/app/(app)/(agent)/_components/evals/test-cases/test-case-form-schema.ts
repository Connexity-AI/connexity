import { z } from 'zod';

import { Difficulty, FirstTurn, TestCaseStatus } from '@/client/types.gen';

import type { TestCasePublic } from '@/client/types.gen';

export const testCaseFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  difficulty: z.enum(Difficulty),
  status: z.enum(TestCaseStatus, { message: 'Please select a status' }),
  tags: z.array(z.string()),
  first_turn: z.enum(FirstTurn),
  first_message: z.string(),
  persona_context: z.string(),
  expected_outcomes: z.array(z.object({ value: z.string() })),
  expected_tool_calls: z.array(
    z.object({
      tool: z.string(),
      expected_params: z.record(z.string(), z.unknown()).nullable(),
    })
  ),
});

export type TestCaseFormValues = z.infer<typeof testCaseFormSchema>;

export interface ToolForValidation {
  name: string;
  parameters: { name: string }[];
}

export function buildTestCaseFormSchema(availableTools: ToolForValidation[]) {
  return testCaseFormSchema.superRefine((values, ctx) => {
    const toolByName = new Map(availableTools.map((tool) => [tool.name, tool]));
    values.expected_tool_calls.forEach((call, callIndex) => {
      const tool = toolByName.get(call.tool);
      if (!tool) return;
      const params = call.expected_params ?? {};
      tool.parameters.forEach((param) => {
        const value = params[param.name];
        const isEmpty =
          value === undefined ||
          value === null ||
          (typeof value === 'string' && value.trim() === '');
        if (isEmpty) {
          ctx.addIssue({
            code: 'custom',
            path: ['expected_tool_calls', callIndex, 'expected_params', param.name],
            message: 'Required',
          });
        }
      });
    });
  });
}

export const TEST_CASE_FORM_EMPTY_DEFAULTS: TestCaseFormValues = {
  name: '',
  difficulty: Difficulty.NORMAL,
  status: TestCaseStatus.ACTIVE,
  tags: [],
  first_turn: FirstTurn.USER,
  first_message: '',
  persona_context: '',
  expected_outcomes: [],
  expected_tool_calls: [],
};

export function computeFormDefaults(testCase: TestCasePublic | null): TestCaseFormValues {
  if (!testCase) return TEST_CASE_FORM_EMPTY_DEFAULTS;
  return testCaseToFormValues(testCase);
}

export function computeFormValues(testCase: TestCasePublic | null): TestCaseFormValues | undefined {
  if (!testCase) return undefined;
  return testCaseToFormValues(testCase);
}

export function testCaseToFormValues(testCase: TestCasePublic): TestCaseFormValues {
  return {
    name: testCase.name,
    difficulty: testCase.difficulty ?? Difficulty.NORMAL,
    status: testCase.status ?? TestCaseStatus.ACTIVE,
    tags: testCase.tags ?? [],
    first_turn: testCase.first_turn ?? FirstTurn.USER,
    first_message: testCase.first_message ?? '',
    persona_context: testCase.persona_context ?? '',
    expected_outcomes: (testCase.expected_outcomes ?? []).map((value) => ({ value })),

    expected_tool_calls:
      testCase.expected_tool_calls?.map((call) => ({
        tool: call.tool,
        expected_params: (call.expected_params ?? null) as Record<string, unknown> | null,
      })) ?? [],
  };
}
