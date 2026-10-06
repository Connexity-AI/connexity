'use client';

import { useParams } from 'next/navigation';

import { Database } from 'lucide-react';

import { TestCasesTable } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-table';
import { useSuspenseTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';

export function TestCasesTab() {
  const { agentId } = useParams<{ agentId: string }>();
  const { data } = useSuspenseTestCases(agentId);

  const testCases = data?.data ?? [];

  if (testCases.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
        <div className="w-14 h-14 rounded-2xl border border-border bg-accent/40 flex items-center justify-center">
          <Database className="w-6 h-6 text-muted-foreground/50" />
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-sm text-foreground">No test cases yet</p>
          <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
            Test cases are created through your assistant and appear here once they exist.
          </p>
        </div>
      </div>
    );
  }

  return <TestCasesTable agentId={agentId} testCases={testCases} />;
}
