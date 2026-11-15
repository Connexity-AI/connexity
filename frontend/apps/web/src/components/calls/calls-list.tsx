import { CallsView } from '@/components/calls/calls-view';
import { CallsService } from '@/client/sdk.gen';

import type { CallCheckStatus } from '@/client/types.gen';
import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;
const RESULTS = ['failed', 'degraded', 'clean', 'unchecked'] as const;
const PAGE = 25;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Period = (typeof PERIODS)[number];

export type SearchParams = Record<string, string | string[] | undefined>;

export const one = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

interface Props {
  params: SearchParams;
  /** On an agent's page: only this agent's calls, without the page bar. */
  agentId?: string;
}

/** The Calls list, read from the address: the Calls page and an agent's Calls tab. */
export const CallsList: FC<Props> = async ({ params, agentId }) => {
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
      agent_id: agentId ?? one(params.agent),
      result,
      category: one(params.category),
      q: one(params.q),
      issue_id: UUID.test(one(params.issue) ?? '') ? one(params.issue) : undefined,
      skip: 0,
      limit: shown,
    },
  });
  if (!response.data) throw new Error('Calls could not be loaded.');

  return (
    <CallsView calls={response.data} shown={shown} pageSize={PAGE} embedded={Boolean(agentId)} />
  );
};
