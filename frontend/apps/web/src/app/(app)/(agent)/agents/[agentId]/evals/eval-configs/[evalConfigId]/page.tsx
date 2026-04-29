import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { EvalConfigDetailSkeleton } from '@/app/(app)/(agent)/_components/evals/eval-configs/eval-config-detail-skeleton';
import { EvalConfigDetailView } from '@/app/(app)/(agent)/_components/evals/eval-configs/eval-config-detail-view';
import { evalConfigDetailQuery } from '@/app/(app)/(agent)/_queries/eval-config-detail-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string; evalConfigId: string }>;
}

export default async function EvalConfigDetailPage({ params }: Props) {
  const { agentId, evalConfigId } = await params;

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(evalConfigDetailQuery(evalConfigId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<EvalConfigDetailSkeleton />}>
          <EvalConfigDetailView agentId={agentId} evalConfigId={evalConfigId} />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
