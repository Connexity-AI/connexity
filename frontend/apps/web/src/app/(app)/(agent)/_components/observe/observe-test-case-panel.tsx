'use client';
'use no memo';

import { Sparkles, X } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { Form } from '@workspace/ui/components/ui/form';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { TestCaseDrawerFooter } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-footer';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';
import { BatchPagerNav } from '@/app/(app)/(agent)/_components/observe/batch-pager-nav';
import { useTestCaseDetailForm } from '@/app/(app)/(agent)/_hooks/use-test-case-detail-form';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import type { TestCasePublic } from '@/client/types.gen';

interface ObserveTestCasePanelProps {
  agentId: string;
  testCase: TestCasePublic | null;
  onClose: () => void;
  onRequestDelete: (testCase: TestCasePublic) => void;
  onOpenAiAssistant?: () => void;
  position?: number;
  total?: number;
  onPrev?: () => void;
  onNext?: () => void;
}

export function ObserveTestCasePanel({
  agentId,
  testCase,
  onClose,
  onRequestDelete,
  onOpenAiAssistant,
  position,
  total,
  onPrev,
  onNext,
}: ObserveTestCasePanelProps) {
  const agentForm = useFormContext<AgentFormValues>();
  const availableTools = agentForm.watch('tools') ?? [];

  const { form, handleSubmit, isPending } = useTestCaseDetailForm({
    agentId,
    testCase,
    availableTools,
    onSuccess: onClose,
  });

  const status = form.watch('status');

  if (!testCase) return null;

  return (
    <div className="flex h-full w-[420px] shrink-0 flex-col overflow-hidden">
      <div className="flex h-[52px] shrink-0 items-center justify-between border-b border-border px-4">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm text-foreground">{testCase.name}</span>
          <StatusBadge status={status} />
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onOpenAiAssistant ? (
            <Button
              type="button"
              variant="outline"
              onClick={onOpenAiAssistant}
              title="AI Assistant"
              className="h-7 gap-1.5 rounded-md border-violet-500/25 bg-violet-500/10 px-2 text-[11px] font-normal text-violet-300 hover:bg-violet-500/20 hover:text-violet-300 [&_svg]:size-3"
            >
              <Sparkles />
              AI Assistant
            </Button>
          ) : null}
          <BatchPagerNav
            current={position ?? 0}
            total={total ?? 0}
            canPrev={Boolean(onPrev)}
            canNext={Boolean(onNext)}
            onPrev={onPrev}
            onNext={onNext}
            prevLabel="Previous test case"
            nextLabel="Next test case"
          />
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            className="h-auto w-auto rounded p-1 text-muted-foreground hover:bg-transparent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Form {...form}>
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
    </div>
  );
}
