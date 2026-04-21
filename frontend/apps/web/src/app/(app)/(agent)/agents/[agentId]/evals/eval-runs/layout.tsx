import { dehydrate } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';
import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';
import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';
import { testCasesListQuery } from '@/app/(app)/(agent)/_queries/test-cases-list-query';
import ErrorBoundary from '@/components/common/error-boundary';
import { HydrateProvider } from '@/components/common/hydrate-provider';

interface Props {
  params: Promise<{ agentId: string }>;
  children: React.ReactNode;
}

export default async function EvalRunsLayout({ params, children }: Props) {
  const { agentId } = await params;

  const queryClient = getQueryClient();

  queryClient.prefetchQuery(evalRunsListQuery(agentId));
  queryClient.prefetchQuery(evalConfigsListQuery(agentId));
  queryClient.prefetchQuery(testCasesListQuery(agentId));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <ErrorBoundary>{children}</ErrorBoundary>
    </HydrateProvider>
  );
}
