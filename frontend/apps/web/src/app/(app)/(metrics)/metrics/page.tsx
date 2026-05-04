import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { CustomMetricService } from '@/app/(app)/(metrics)/_service';
import { MetricsPage } from '@/app/(app)/(metrics)/metrics/_components/metrics-page';
import { MetricsPageSkeleton } from '@/app/(app)/(metrics)/metrics/_components/metrics-page-skeleton';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

export default async function MetricsRoutePage() {
  const queryClient = getQueryClient();

  queryClient.prefetchQuery(CustomMetricService.getCustomMetricsQuery());

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<MetricsPageSkeleton />}>
          <MetricsPage />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
