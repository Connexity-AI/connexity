import { createPublicEnv } from 'next-public-env';

import { getProcessEnvSchemaProps } from '@/schemas/config';

/** Exports RUNTIME env. Must NOT call getPublicEnv() in global scope. */
export const { getPublicEnv, PublicEnv } = createPublicEnv(
  {
    NODE_ENV: process.env.NODE_ENV,
    SITE_URL: process.env.SITE_URL,
    API_URL: process.env.API_URL,
  },
  { schema: (z) => getProcessEnvSchemaProps(z) }
);
