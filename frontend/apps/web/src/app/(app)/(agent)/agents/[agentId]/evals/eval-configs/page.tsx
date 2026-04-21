import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { EvalConfigsTable } from '@/app/(app)/(agent)/_components/evals/eval-configs/eval-configs-table';
import { EvalConfigsTableSkeleton } from '@/app/(app)/(agent)/_components/evals/eval-configs/eval-configs-table-skeleton';
import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function EvalConfigsPage({ params }: Props) {
  const { agentId } = await params;

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(evalConfigsListQuery(agentId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<EvalConfigsTableSkeleton />}>
          <EvalConfigsTable agentId={agentId} />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
