import { CallsList } from '@/components/calls/calls-list';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';

import type { SearchParams } from '@/components/calls/calls-list';
import type { FC } from 'react';

interface Props {
  searchParams: Promise<SearchParams>;
}

/** Calls (designs/screens/Connexity Calls.dc.html; plans/2026-11-13-calls-page.md). */
const CallsPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <CallsList params={params} />
    </ErrorBoundarySuspense>
  );
};

export default CallsPage;
