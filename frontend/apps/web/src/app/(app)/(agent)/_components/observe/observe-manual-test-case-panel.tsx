'use client';
'use no memo';

import { Loader2, Sparkles, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Form } from '@workspace/ui/components/ui/form';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';
import { useManualTestCaseForm } from '@/app/(app)/(agent)/_components/evals/test-cases/use-manual-test-case-form';

import type { CallPublic } from '@/client/types.gen';

interface ObserveManualTestCasePanelProps {
  agentId: string;
  call?: CallPublic | null;
  onClose: () => void;
  onOpenAiAssistant?: () => void;
}

export function ObserveManualTestCasePanel({
  agentId,
  call,
  onClose,
  onOpenAiAssistant,
}: ObserveManualTestCasePanelProps) {
  const { form, availableTools, handleSubmit, name, status, isPending, error, onOpenChange } =
    useManualTestCaseForm({
      agentId,
      sourceCallId: call?.id ?? null,
      onOpenChange: (open) => {
        if (!open) onClose();
      },
    });

  return (
    <div className="flex h-full w-[420px] shrink-0 flex-col overflow-hidden">
      <div className="flex h-[52px] shrink-0 items-center justify-between border-b border-border px-4">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm text-foreground">
            {name?.trim() ? name : 'New test case'}
          </span>
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
          <button
            type="button"
            onClick={() => onOpenChange(false)}
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

          <div className="flex shrink-0 flex-col gap-2 border-t border-border px-4 py-3">
            {error ? (
              <p className="text-xs text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                className="h-7 gap-1.5 text-xs"
                disabled={isPending}
              >
                {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Create test case
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </div>
  );
}
