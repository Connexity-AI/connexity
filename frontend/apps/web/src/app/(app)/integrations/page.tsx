import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { integrationsListQuery } from '@/app/(app)/(agent)/_queries/integrations-list-query';
import { IntegrationsClient } from '@/app/(app)/integrations/_components/integrations-client';
import { IntegrationsClientSkeleton } from '@/app/(app)/integrations/_components/integrations-client-skeleton';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

export default async function IntegrationsPage() {
  const queryClient = getQueryClient();

  queryClient.prefetchQuery(integrationsListQuery());

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>
        <Suspense fallback={<IntegrationsClientSkeleton />}>
          <IntegrationsClient />
        </Suspense>
      </ErrorBoundary>
    </HydrateProvider>
  );
}
