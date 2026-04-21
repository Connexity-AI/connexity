import { Suspense } from 'react';

import { EvalRunsView } from '@/app/(app)/(agent)/_components/evals/eval-runs/eval-runs-view';
import { EvalRunsViewSkeleton } from '@/app/(app)/(agent)/_components/evals/eval-runs/eval-runs-view-skeleton';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function EvalRunsPage({ params }: Props) {
  const { agentId } = await params;

  return (
    <Suspense fallback={<EvalRunsViewSkeleton />}>
      <EvalRunsView agentId={agentId} />
    </Suspense>
  );
}
