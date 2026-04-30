import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { environmentsListQuery } from '@/app/(app)/(agent)/_queries/environments-list-query';
import { integrationsListQuery } from '@/app/(app)/(agent)/_queries/integrations-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';
import {
  EnvironmentsSection,
  EnvironmentsSectionSkeleton,
} from './_components/environments-section';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function AgentDeployPage({ params }: Props) {
  const { agentId } = await params;

  const queryClient = getQueryClient();
  queryClient.prefetchQuery(environmentsListQuery(agentId));
  queryClient.prefetchQuery(integrationsListQuery());

  const dehydratedState = dehydrate(queryClient);

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        <HydrateProvider state={dehydratedState}>
          <ErrorBoundary>
            <Suspense fallback={<EnvironmentsSectionSkeleton />}>
              <EnvironmentsSection agentId={agentId} />
            </Suspense>
          </ErrorBoundary>
        </HydrateProvider>
      </div>
    </div>
  );
}
