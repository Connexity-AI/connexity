'use client';

import { SectionLabel } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';
import { TestCaseExpectedOutcomesField } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-expected-outcomes-field';
import { TestCaseExpectedToolCallsField } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-expected-tool-calls-field';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

type AgentTool = AgentFormValues['tools'][number];

export function TestCaseEvaluationSection({ availableTools }: { availableTools: AgentTool[] }) {
  return (
    <div>
      <SectionLabel>Evaluation</SectionLabel>

      <div className="space-y-4">
        <TestCaseExpectedOutcomesField />

        <TestCaseExpectedToolCallsField availableTools={availableTools} />
      </div>
    </div>
  );
}
