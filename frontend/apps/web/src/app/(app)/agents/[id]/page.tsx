import { notFound } from 'next/navigation';

import { AgentView } from '@/components/agents/agent-view';
import { CallsList, one } from '@/components/calls/calls-list';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgentsService } from '@/client/sdk.gen';

import type { SearchParams } from '@/components/calls/calls-list';
import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;

const Agent: FC<{ id: string; params: SearchParams }> = async ({ id, params }) => {
  const period = PERIODS.find((p) => p === one(params.period)) ?? '30d';
  const response = await AgentsService.getAgentPage({
    path: { agent_id: id },
    query: { period },
  });
  if (response.response?.status === 404 || response.response?.status === 422) notFound();
  if (!response.data) throw new Error('The agent could not be loaded.');
  const tab = one(params.tab) === 'calls' ? 'calls' : 'overview';

  return (
    <AgentView agent={response.data} tab={tab}>
      {tab === 'calls' ? <CallsList params={params} agentId={id} /> : null}
    </AgentView>
  );
};

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<SearchParams>;
}

/**
 * One agent (designs/screens/Connexity Agent Profile.dc.html; plans/2026-11-14-agent-page.md).
 */
const AgentPage: FC<Props> = async ({ params, searchParams }) => {
  const { id } = await params;
  const search = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Agent id={id} params={search} />
    </ErrorBoundarySuspense>
  );
};

export default AgentPage;
