import { CallsView } from '@/components/calls/calls-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { CallsService } from '@/client/sdk.gen';

import type { CallCheckStatus } from '@/client/types.gen';
import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;
const RESULTS = ['failed', 'degraded', 'clean', 'unchecked'] as const;
const PAGE = 25;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Period = (typeof PERIODS)[number];

type SearchParams = Record<string, string | string[] | undefined>;

const one = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

const Calls: FC<{ params: SearchParams }> = async ({ params }) => {
  const periodParam = one(params.period);
  const period: Period = PERIODS.includes(periodParam as Period) ? (periodParam as Period) : '30d';
  const resultParam = one(params.result);
  const result = RESULTS.includes(resultParam as (typeof RESULTS)[number])
    ? (resultParam as CallCheckStatus)
    : undefined;
  const shown = Math.min(Math.max(Number(one(params.shown)) || PAGE, PAGE), 500);

  const response = await CallsService.listCalls({
    query: {
      period,
      agent_id: one(params.agent),
      result,
      category: one(params.category),
      q: one(params.q),
      issue_id: UUID.test(one(params.issue) ?? '') ? one(params.issue) : undefined,
      skip: 0,
      limit: shown,
    },
  });
  if (!response.data) throw new Error('Calls could not be loaded.');

  return <CallsView calls={response.data} shown={shown} pageSize={PAGE} />;
};

interface Props {
  searchParams: Promise<SearchParams>;
}

/** Calls (designs/screens/Connexity Calls.dc.html; plans/2026-11-13-calls-page.md). */
const CallsPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Calls params={params} />
    </ErrorBoundarySuspense>
  );
};

export default CallsPage;
