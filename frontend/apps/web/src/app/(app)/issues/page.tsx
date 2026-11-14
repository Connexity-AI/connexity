import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { IssuesView } from '@/components/issues/issues-view';
import { IssuesService } from '@/client/sdk.gen';

import type { FC } from 'react';

const PERIODS = ['7d', '30d', '90d'] as const;
const SEVERITIES = ['critical', 'warning'] as const;
const STATUSES = ['open', 'reopened', 'resolved', 'archived'] as const;

type SearchParams = Record<string, string | string[] | undefined>;

const one = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

const pick = <T extends string>(allowed: readonly T[], value: string | undefined) =>
  allowed.includes(value as T) ? (value as T) : undefined;

const Issues: FC<{ params: SearchParams }> = async ({ params }) => {
  const response = await IssuesService.listIssues({
    query: {
      period: pick(PERIODS, one(params.period)) ?? '30d',
      agent_id: one(params.agent),
      category: one(params.category),
      severity: pick(SEVERITIES, one(params.severity)),
      status: pick(STATUSES, one(params.status)) ?? 'open',
      q: one(params.q),
    },
  });
  if (!response.data) throw new Error('Issues could not be loaded.');

  return <IssuesView issues={response.data} />;
};

interface Props {
  searchParams: Promise<SearchParams>;
}

/** Issues (designs/screens/Connexity Issues.dc.html; plans/2026-11-13-issues-page.md). */
const IssuesPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Issues params={params} />
    </ErrorBoundarySuspense>
  );
};

export default IssuesPage;
