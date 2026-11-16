import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { ReadinessView } from '@/components/readiness/readiness-view';
import { ReadinessService } from '@/client/sdk.gen';

import type { FC } from 'react';

/**
 * Where a signed-in person lands. Until the workspace's first scan is done, Readiness
 * is the whole screen (12-adjustments.md item 19); then Work (docs-internal/work.md
 * decision 20). Roadmap feature 10.129 turns onboarding into Work's rows and makes
 * Work the landing from sign-up.
 *
 * Read before rendering, outside any error boundary, so the redirect is never caught.
 */
const HomePage: FC = async () => {
  const result = await ReadinessService.readReadiness();
  if (!result.data) throw new Error('Readiness could not be loaded.');
  if (result.data.first_scan_done) redirect(UrlGenerator.work());

  return <ReadinessView readiness={result.data} />;
};

export default HomePage;
