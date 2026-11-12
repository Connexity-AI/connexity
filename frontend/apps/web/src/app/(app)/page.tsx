import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { ReadinessView } from '@/components/readiness/readiness-view';
import { ReadinessService } from '@/client/sdk.gen';

import type { FC } from 'react';

const Readiness: FC = async () => {
  const result = await ReadinessService.readReadiness();
  if (!result.data) throw new Error('Readiness could not be loaded.');

  return <ReadinessView readiness={result.data} />;
};

/**
 * Where a signed-in person lands. Until the workspace's first scan is done, Readiness
 * is the whole screen (12-adjustments.md item 19). What opens after the first scan is
 * decided with roadmap feature 10.
 */
const HomePage: FC = () => (
  <ErrorBoundarySuspense fallback={null}>
    <Readiness />
  </ErrorBoundarySuspense>
);

export default HomePage;
