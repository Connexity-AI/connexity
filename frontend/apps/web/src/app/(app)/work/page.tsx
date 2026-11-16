import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { WorkView } from '@/components/work/work-view';
import { WorkService } from '@/client/sdk.gen';

import type { FC } from 'react';

const Work: FC = async () => {
  const result = await WorkService.readWork();
  if (!result.data) throw new Error('Work could not be loaded.');

  return <WorkView work={result.data} />;
};

/**
 * Work (designs/16-work.md, designs/screens/Connexity Work.dc.html;
 * plans/2026-11-16-work-page.md): the assistant's tasks in Connexity's order, who is
 * working on what, what waits for the person, and what was done this week.
 */
const WorkPage: FC = () => (
  <ErrorBoundarySuspense fallback={null}>
    <Work />
  </ErrorBoundarySuspense>
);

export default WorkPage;
