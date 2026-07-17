import { Suspense } from 'react';

import { EvalRunsView } from '@/app/(app)/(agent)/_components/evals/eval-runs/eval-runs-view';
import { EvalRunsViewSkeleton } from '@/app/(app)/(agent)/_components/evals/eval-runs/eval-runs-view-skeleton';

// agentId comes from the [agentId] route segment; the client view reads it via
// useParams (per the tanstack-streaming pattern) rather than receiving it as a
// prop, which keeps the suspense query's identity stable across transitions.
export default function EvalRunsPage() {
  return (
    <Suspense fallback={<EvalRunsViewSkeleton />}>
      <EvalRunsView />
    </Suspense>
  );
}
