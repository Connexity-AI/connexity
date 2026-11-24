import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { DashboardView } from '@/components/dashboard/dashboard-view';
import { DashboardService } from '@/client/sdk.gen';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { redirect } from 'next/navigation';

import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;

type SearchParams = Record<string, string | string[] | undefined>;

const one = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

const Dashboard: FC<{ params: SearchParams }> = async ({ params }) => {
  const period = PERIODS.find((p) => p === one(params.period)) ?? '30d';
  const agent = one(params.agent);
  const response = await DashboardService.readDashboard({ query: { period, agent_id: agent } });
  // An agent that is not this workspace's (a stale link) falls back to all agents.
  if (agent && !response.data) redirect(UrlGenerator.dashboard({ period }));
  if (!response.data) throw new Error('The dashboard could not be loaded.');
  return <DashboardView dashboard={response.data} />;
};

interface Props {
  searchParams: Promise<SearchParams>;
}

/** The Dashboard (designs/screens/Connexity Home.dc.html; plans/2026-11-18-dashboard.md):
 * where the workspace stands, for all agents or one, over a period. */
const DashboardPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;
  return (
    <ErrorBoundarySuspense fallback={null}>
      <Dashboard params={params} />
    </ErrorBoundarySuspense>
  );
};

export default DashboardPage;
