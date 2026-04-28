'use client';
'use no memo';

import { useMemo } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useFormContext } from 'react-hook-form';

import {
  buildTestCaseFormSchema,
  TEST_CASE_FORM_EMPTY_DEFAULTS,
  type TestCaseFormValues,
} from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';
import { useCreateTestCase } from '@/app/(app)/(agent)/_hooks/use-create-test-case';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import type { TestCaseCreate } from '@/client/types.gen';

const PERSONA_CONTEXT_TEMPLATE =
  '[Persona type]\n\n\n[Description]\n\n\n[Behavioral instructions]\n';

const ADD_TEST_CASE_DEFAULTS: TestCaseFormValues = {
  ...TEST_CASE_FORM_EMPTY_DEFAULTS,
  persona_context: PERSONA_CONTEXT_TEMPLATE,
};

interface UseManualTestCaseFormOptions {
  agentId: string;
  sourceCallId?: string | null;
  onOpenChange: (open: boolean) => void;
}

function formValuesToCreatePayload(
  values: TestCaseFormValues,
  agentId: string,
  sourceCallId: string | null | undefined
): TestCaseCreate {
  return {
    name: values.name,
    difficulty: values.difficulty,
    status: values.status,
    tags: values.tags,
    first_turn: values.first_turn,
    first_message: values.first_message,
    persona_context: values.persona_context,
    expected_outcomes: values.expected_outcomes.map((o) => o.value),
    expected_tool_calls: values.expected_tool_calls.map((call) => ({
      tool: call.tool,
      expected_params: call.expected_params,
    })),
    agent_id: agentId,
    source_call_id: sourceCallId ?? null,
  };
}

export function useManualTestCaseForm({
  agentId,
  sourceCallId,
  onOpenChange,
}: UseManualTestCaseFormOptions) {
  const agentForm = useFormContext<AgentFormValues>();
  const watchedTools = agentForm.watch('tools');
  const availableTools = useMemo(() => watchedTools ?? [], [watchedTools]);

  const schema = useMemo(() => buildTestCaseFormSchema(availableTools), [availableTools]);

  const form = useForm<TestCaseFormValues>({
    resolver: zodResolver(schema),
    defaultValues: ADD_TEST_CASE_DEFAULTS,
  });

  const { mutateAsync, isPending, error } = useCreateTestCase(agentId);

  const handleOpenChange = (next: boolean) => {
    if (!next) form.reset(ADD_TEST_CASE_DEFAULTS);
    onOpenChange(next);
  };

  const submit = async (values: TestCaseFormValues) => {
    await mutateAsync(formValuesToCreatePayload(values, agentId, sourceCallId));
    handleOpenChange(false);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    void form.handleSubmit(submit)(event);
  };

  const name = form.watch('name');
  const status = form.watch('status');

  return {
    form,
    availableTools,
    handleSubmit,
    name,
    status,
    isPending,
    error,
    onOpenChange: handleOpenChange,
  };
}
