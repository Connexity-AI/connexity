'use client';
'use no memo';

import { Button } from '@workspace/ui/components/ui/button';
import { Form } from '@workspace/ui/components/ui/form';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@workspace/ui/components/ui/sheet';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { useManualTestCaseForm } from '@/app/(app)/(agent)/_components/evals/test-cases/use-manual-test-case-form';

interface AddTestCaseManualDrawerProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddTestCaseManualDrawer({
  agentId,
  open,
  onOpenChange,
}: AddTestCaseManualDrawerProps) {
  const {
    form,
    availableTools,
    handleSubmit,
    name,
    status,
    isPending,
    error,
    onOpenChange: handleOpenChange,
  } = useManualTestCaseForm({ agentId, onOpenChange });

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent
        side="right"
        className="flex h-full w-full flex-col gap-0 overflow-hidden border-l border-border p-0 sm:max-w-120"
      >
        <Form {...form}>
          <SheetHeader className="flex h-13 shrink-0 flex-row items-center justify-between space-y-0 border-b border-border px-4 text-left">
            <div className="flex min-w-0 items-center gap-2">
              <SheetTitle className="truncate text-sm font-normal text-foreground">
                {name?.trim() ? name : 'New test case'}
              </SheetTitle>
              <StatusBadge status={status} />
            </div>
          </SheetHeader>

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
                  onClick={() => handleOpenChange(false)}
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
                  {isPending ? 'Creating…' : 'Create test case'}
                </Button>
              </div>
            </div>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
