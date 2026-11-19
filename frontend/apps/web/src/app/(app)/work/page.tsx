import { Suspense } from 'react';
import { dehydrate } from '@tanstack/react-query';

import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { HydrateProvider } from '@/components/common/hydrate-provider';
import { WorkView } from '@/components/work/work-view';
import { workQuery } from '@/components/work/work-query';
import getQueryClient from '@/lib/react-query/getQueryClient';

import type { FC } from 'react';

const Work: FC = async () => {
  const queryClient = getQueryClient();
  // Awaited: the list is the page, so it is in the first HTML; the view then polls it.
  await queryClient.prefetchQuery(workQuery());

  return (
    <HydrateProvider state={dehydrate(queryClient)}>
      <Suspense fallback={null}>
        <WorkView />
      </Suspense>
    </HydrateProvider>
  );
};

/**
 * Work (designs/16-work.md, designs/screens/Connexity Work.dc.html;
 * plans/2026-11-16-work-page.md): the assistant's tasks in Connexity's order, who is
 * working on what, what waits for the person, and what was done this week. It reloads
 * by itself every 10 seconds while open (plans/2026-11-19-work-updates-itself.md).
 */
const WorkPage: FC = () => (
  <ErrorBoundarySuspense fallback={null}>
    <Work />
  </ErrorBoundarySuspense>
);

export default WorkPage;
