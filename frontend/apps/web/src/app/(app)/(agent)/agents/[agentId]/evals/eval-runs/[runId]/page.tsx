import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { EvalRunDetailView } from '@/app/(app)/(agent)/_components/evals/eval-runs/eval-run-detail-view';
import { evalRunDetailQuery } from '@/app/(app)/(agent)/_queries/eval-run-detail-query';
import { testCaseResultsByRunQuery } from '@/app/(app)/(agent)/_queries/test-case-results-by-run-query';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string; runId: string }>;
}

export default async function EvalRunDetailPage({ params }: Props) {
  const { agentId, runId } = await params;

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(evalRunDetailQuery(runId));
  queryClient.prefetchQuery(testCaseResultsByRunQuery(runId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <EvalRunDetailView agentId={agentId} runId={runId} />
    </HydrateProvider>
  );
}
