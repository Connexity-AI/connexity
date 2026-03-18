import { MetadataRoute } from 'next';

import { removeTrailingSlash } from '@/utils/path';
import { ROUTES } from '@/constants/routes';
import { getPublicEnv } from '@/config/process-env';

export const dynamic = 'force-static';

// Todo: not important for dashboard, remove its routes
const sitemap = (): MetadataRoute.Sitemap => {
  const { SITE_URL } = getPublicEnv();

  // only 1st level routes for now
  const oneLevelRoutes = Object.values(ROUTES).filter(
    (v): v is Exclude<typeof v, object> => typeof v === 'string'
  );

  // trim trailing '/' only
  const trimmedRoutes = Object.values(oneLevelRoutes)
    .filter((v): v is Exclude<typeof v, object> => typeof v === 'string')
    .map(removeTrailingSlash);

  const routes = trimmedRoutes.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: new Date().toISOString().split('T')[0],
  }));

  return [...routes];
};

export default sitemap;
