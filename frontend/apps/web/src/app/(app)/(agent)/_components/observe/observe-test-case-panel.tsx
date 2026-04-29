'use client';
'use no memo';

import { ChevronLeft, ChevronRight, Sparkles, X } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Form } from '@workspace/ui/components/ui/form';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { TestCaseDrawerFooter } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-footer';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';
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
  const showBatchNav = total !== undefined && total > 1;

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
            <button
              type="button"
              onClick={onOpenAiAssistant}
              title="AI Assistant"
              className="flex h-7 items-center gap-1.5 rounded-md border border-violet-500/25 bg-violet-500/10 px-2 text-[11px] text-violet-300 transition-colors hover:bg-violet-500/20"
            >
              <Sparkles className="h-3 w-3" />
              AI Assistant
            </button>
          ) : null}
          {showBatchNav ? (
            <div className="flex items-center gap-0.5 rounded-md border border-border bg-accent/40 px-1 py-0.5">
              <button
                type="button"
                onClick={onPrev}
                disabled={!onPrev}
                className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span className="min-w-[34px] px-1 text-center text-[11px] tabular-nums text-foreground">
                {position} / {total}
              </span>
              <button
                type="button"
                onClick={onNext}
                disabled={!onNext}
                className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
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
