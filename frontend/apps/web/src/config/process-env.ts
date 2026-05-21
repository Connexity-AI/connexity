import { createPublicEnv } from 'next-public-env';

import { getProcessEnvSchemaProps } from '@/schemas/config';

const derivedSiteUrl =
  process.env.SITE_URL ||
  (process.env.RAILWAY_PUBLIC_DOMAIN
    ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}`
    : undefined);

/** Exports RUNTIME env. Must NOT call getPublicEnv() in global scope. */
export const { getPublicEnv, PublicEnv } = createPublicEnv(
  {
    NODE_ENV: process.env.NODE_ENV,
    SITE_URL: derivedSiteUrl,
    API_URL: process.env.API_URL,
  },
  { schema: (zod) => getProcessEnvSchemaProps(zod) }
);
