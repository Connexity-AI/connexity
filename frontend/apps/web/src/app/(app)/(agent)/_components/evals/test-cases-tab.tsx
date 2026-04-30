'use client';

import { useState } from 'react';

import { Coffee, Database, Loader2, Plus, Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { GenerateTestCasesDialog } from '@/app/(app)/(agent)/_components/evals/generate-test-cases-dialog';
import { TestCasesTable } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-table';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useGenerateTestCases } from '@/app/(app)/(agent)/_hooks/use-generate-test-cases';
import { useSuspenseTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';

export function TestCasesTab() {
  const { agentId } = useAgentEditFormActions();
  const { data } = useSuspenseTestCases(agentId);
  const { mutate: generate, isPending } = useGenerateTestCases(agentId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [justQueued, setJustQueued] = useState(false);

  const handleGenerate = (payload: { count: number; model: string }) => {
    generate(payload);
    setJustQueued(true);
  };

  const isGenerating = justQueued && isPending;
  const isEmpty = (data?.count ?? 0) === 0;
  const testCases = data?.data ?? [];

  if (isGenerating) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-8 text-center">
        <div className="w-16 h-16 rounded-2xl border border-violet-500/30 bg-violet-500/10 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-base text-foreground">Test cases are being generated…</p>
          <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
            Refresh the page in a few minutes to see the results.
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-accent/30">
          <Coffee className="w-4 h-4 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">Perfect time to grab a coffee</p>
        </div>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <>
        <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
          <div className="w-14 h-14 rounded-2xl border border-border bg-accent/40 flex items-center justify-center">
            <Database className="w-6 h-6 text-muted-foreground/50" />
          </div>
          <div className="flex flex-col gap-1.5">
            <p className="text-sm text-foreground">No test cases yet</p>
            <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
              Generate test cases from your current agent version to start evaluating your
              agent&apos;s behaviour.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" className="gap-2" onClick={() => setDialogOpen(true)}>
              <Sparkles className="w-3.5 h-3.5" />
              Generate Test Cases
            </Button>

            <Button size="sm" variant="outline" className="gap-1.5" disabled>
              <Plus className="w-3.5 h-3.5" />
              Add test case
            </Button>
          </div>
        </div>

        <GenerateTestCasesDialog
          agentId={agentId}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onGenerate={handleGenerate}
        />
      </>
    );
  }

  return (
    <>
      <TestCasesTable agentId={agentId} testCases={testCases} />

      <GenerateTestCasesDialog
        agentId={agentId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onGenerate={handleGenerate}
      />
    </>
  );
}
