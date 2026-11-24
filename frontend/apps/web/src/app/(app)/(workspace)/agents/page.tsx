import { AgentsView } from '@/components/agents/agents-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgentsService } from '@/client/sdk.gen';

import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;

type SearchParams = Record<string, string | string[] | undefined>;

const Agents: FC<{ params: SearchParams }> = async ({ params }) => {
  const raw = Array.isArray(params.period) ? params.period[0] : params.period;
  const period = PERIODS.find((p) => p === raw) ?? '30d';
  const response = await AgentsService.listWorkspaceAgents({ query: { period } });
  if (!response.data) throw new Error('Agents could not be loaded.');

  return <AgentsView agents={response.data} />;
};

interface Props {
  searchParams: Promise<SearchParams>;
}

/** Agents (designs/screens/Connexity Agents.dc.html; plans/2026-11-14-agents-page.md). */
const AgentsPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Agents params={params} />
    </ErrorBoundarySuspense>
  );
};

export default AgentsPage;
