import { MetadataRoute } from 'next';

import { getPublicEnv } from '@/config/process-env';

export const dynamic = 'force-static';

const robots = (): MetadataRoute.Robots => {
  const { SITE_URL } = getPublicEnv();

  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
};

export default robots;
