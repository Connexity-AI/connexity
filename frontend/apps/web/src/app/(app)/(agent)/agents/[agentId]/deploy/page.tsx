import { Suspense } from 'react';

import { dehydrate } from '@tanstack/react-query';

import { listIntegrations } from '@/actions/integrations';
import { environmentsListQuery } from '@/app/(app)/(agent)/_queries/environments-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';
import getQueryClient from '@/lib/react-query/getQueryClient';
import { isSuccessApiResult } from '@/utils/api';

import {
  EnvironmentsSection,
  EnvironmentsSectionSkeleton,
} from './_components/environments-section';

import type { IntegrationPublic } from '@/client/types.gen';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function AgentDeployPage({ params }: Props) {
  const { agentId } = await params;

  const result = await listIntegrations();
  const integrations: IntegrationPublic[] = isSuccessApiResult(result) ? result.data.data : [];

  const queryClient = getQueryClient();
  queryClient.prefetchQuery(environmentsListQuery(agentId));
  const dehydratedState = dehydrate(queryClient);

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        <HydrateProvider state={dehydratedState}>
          <ErrorBoundary>
            <Suspense fallback={<EnvironmentsSectionSkeleton />}>
              <EnvironmentsSection agentId={agentId} integrations={integrations} />
            </Suspense>
          </ErrorBoundary>
        </HydrateProvider>
      </div>
    </div>
  );
}
