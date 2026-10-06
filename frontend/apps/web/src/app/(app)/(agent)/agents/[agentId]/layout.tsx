import { dehydrate } from '@tanstack/react-query';

import { AgentHeader } from '@/app/(app)/(agent)/_components/header/agent-header';
import { agentDetailQuery } from '@/app/(app)/(agent)/_queries/agent-detail-query';
import { appConfigQueries } from '@/app/(app)/(agent)/_queries/app-config-query';
import getQueryClient from '@/lib/react-query/getQueryClient';
import { HydrateProvider } from '@/components/common/hydrate-provider';

import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  params: Promise<{ agentId: string }>;
}

export default async function AgentLayout({ children, params }: Props) {
  const { agentId } = await params;

  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.prefetchQuery(appConfigQueries.root),
    queryClient.prefetchQuery(agentDetailQuery(agentId)),
  ]);

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <AgentHeader />
      {children}
    </HydrateProvider>
  );
}
