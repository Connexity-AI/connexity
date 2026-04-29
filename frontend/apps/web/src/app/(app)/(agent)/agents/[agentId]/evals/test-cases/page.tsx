import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { TestCasesTab } from '@/app/(app)/(agent)/_components/evals/test-cases-tab';
import { TestCasesTabSkeleton } from '@/app/(app)/(agent)/_components/evals/test-cases/test-cases-tab-skeleton';
import { testCasesListQuery } from '@/app/(app)/(agent)/_queries/test-cases-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function TestCasesPage({ params }: Props) {
  const { agentId } = await params;

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(testCasesListQuery(agentId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<TestCasesTabSkeleton />}>
          <TestCasesTab />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
