'use client';

import { useMemo } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import {
  buildTestCaseFormSchema,
  computeFormDefaults,
  computeFormValues,
  type TestCaseFormValues,
  type ToolForValidation,
} from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';
import { useUpdateTestCase } from '@/app/(app)/(agent)/_hooks/use-update-test-case';

import type { ExpectedToolCall, TestCasePublic } from '@/client/types.gen';

interface UseTestCaseDetailFormParams {
  agentId: string;
  testCase: TestCasePublic | null;
  availableTools: ToolForValidation[];
  onSuccess: () => void;
}

export function useTestCaseDetailForm({
  agentId,
  testCase,
  availableTools,
  onSuccess,
}: UseTestCaseDetailFormParams) {
  const { mutateAsync, isPending } = useUpdateTestCase(agentId);

  const schema = useMemo(() => buildTestCaseFormSchema(availableTools), [availableTools]);

  const form = useForm<TestCaseFormValues>({
    resolver: zodResolver(schema),
    defaultValues: computeFormDefaults(testCase),
    values: computeFormValues(testCase),
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    if (!testCase) return;
    const outcomes = values.expected_outcomes
      .map((outcome) => outcome.value)
      .filter((outcome) => outcome.trim() !== '');
    const toolCalls: ExpectedToolCall[] = values.expected_tool_calls
      .filter((call) => call.tool)
      .map((call) => ({ tool: call.tool, expected_params: call.expected_params }));
    await mutateAsync({
      testCaseId: testCase.id,
      body: {
        name: values.name,
        difficulty: values.difficulty,
        status: values.status,
        tags: values.tags,
        first_turn: values.first_turn,
        first_message: values.first_message || null,
        persona_context: values.persona_context || null,
        expected_outcomes: outcomes,
        expected_tool_calls: toolCalls,
      },
    });
    onSuccess();
  });

  return { form, handleSubmit, isPending };
}
