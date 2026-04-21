import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { CreateEvalView } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-view';
import { EvalConfigDetailSkeleton } from '@/app/(app)/(agent)/_components/evals/eval-configs/eval-config-detail-skeleton';
import { availableMetricsQuery } from '@/app/(app)/(agent)/_queries/available-metrics-query';
import { testCasesListQuery } from '@/app/(app)/(agent)/_queries/test-cases-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string }>;
  searchParams: Promise<{ ids?: string }>;
}

export default async function CreateEvalPage({ params, searchParams }: Props) {
  const [{ agentId }, { ids }] = await Promise.all([params, searchParams]);
  const initialTestCaseIds = ids ? ids.split(',').filter(Boolean) : [];

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(availableMetricsQuery());
  queryClient.prefetchQuery(testCasesListQuery(agentId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<EvalConfigDetailSkeleton />}>
          <CreateEvalView agentId={agentId} initialTestCaseIds={initialTestCaseIds} />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
