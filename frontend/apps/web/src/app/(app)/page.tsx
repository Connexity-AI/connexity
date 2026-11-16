import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

/**
 * Where a signed-in person lands: Work, where onboarding is the first rows of the
 * list (docs-internal/work.md decisions 20 and 21; plans/2026-11-16-onboarding-on-work.md).
 */
const HomePage = () => redirect(UrlGenerator.work());

export default HomePage;
