'use client';
'use no memo';

import { useFormContext } from 'react-hook-form';

import { Form } from '@workspace/ui/components/ui/form';
import { Sheet, SheetContent } from '@workspace/ui/components/ui/sheet';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { TestCaseDrawerFooter } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-footer';
import { TestCaseDrawerHeader } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-header';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { useTestCaseDetailForm } from '@/app/(app)/(agent)/_hooks/use-test-case-detail-form';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import type { TestCasePublic } from '@/client/types.gen';

interface TestCaseDetailDrawerProps {
  agentId: string;
  testCase: TestCasePublic | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRequestDelete: (testCase: TestCasePublic) => void;
}

export function TestCaseDetailDrawer({
  agentId,
  testCase,
  open,
  onOpenChange,
  onRequestDelete,
}: TestCaseDetailDrawerProps) {
  const agentForm = useFormContext<AgentFormValues>();
  const availableTools = agentForm.watch('tools') ?? [];

  const { form, handleSubmit, isPending } = useTestCaseDetailForm({
    agentId,
    testCase,
    availableTools,
    onSuccess: () => onOpenChange(false),
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex h-full w-full flex-col gap-0 overflow-hidden border-l border-border p-0 sm:max-w-120"
      >
        <Form {...form}>
          <TestCaseDrawerHeader testCaseName={testCase?.name} />

          <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 overflow-auto">
              <div className="space-y-6 px-5 py-5">
                <TestCaseBasicInfoSection />

                <TestCaseUserSimulationSection />

                <TestCaseEvaluationSection availableTools={availableTools} />
              </div>
            </div>
            <TestCaseDrawerFooter
              testCase={testCase}
              isPending={isPending}
              onRequestDelete={onRequestDelete}
            />
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
