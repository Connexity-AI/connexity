import { MetadataRoute } from 'next';

import { removeTrailingSlash } from '@/utils/path';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { getPublicEnv } from '@/config/process-env';

export const dynamic = 'force-static';

// Todo: not important for dashboard, remove its routes
const sitemap = (): MetadataRoute.Sitemap => {
  const { SITE_URL } = getPublicEnv();

  const sitemapRoutes = [
    UrlGenerator.home(),
    UrlGenerator.login(),
    UrlGenerator.register(),
    UrlGenerator.forgotPassword(),
    UrlGenerator.dashboard(),
    UrlGenerator.agents(),
    UrlGenerator.metrics(),
  ];

  const routes = sitemapRoutes.map((route) => ({
    url: `${SITE_URL}${removeTrailingSlash(route)}`,
    lastModified: new Date().toISOString().split('T')[0],
  }));

  return [...routes];
};

export default sitemap;
