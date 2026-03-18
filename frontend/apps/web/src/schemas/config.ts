import { z } from 'zod';

export const nodeEnvValues = ['development', 'test', 'production'] as const;
export const booleanValues = ['true', 'false', ''] as const;
export const modeValues = ['light', 'dark'] as const;

type ZodType = typeof z;

/** For runtime env. */
export const getProcessEnvSchemaProps = (z: ZodType) => ({
  NODE_ENV: z.enum(nodeEnvValues),
  // Note: these are actually REQUIRED variables but declared optional for logging in global-error.tsx.
  // Propagate exception to rendering phase and handle it in src/app/page.tsx, where it's again enforced as required.
  // This is done for better dev experience during initial setup.
  SITE_URL: z.url().regex(/[^/]$/, 'SITE_URL should not end with a slash "/"').optional(),
  API_URL: z.url().regex(/[^/]$/, 'API_URL should not end with a slash "/"').optional(),
});

/** For schema type. */
export const processEnvSchema = z.object(getProcessEnvSchemaProps(z));

export const configClientSchema = z.object({
  PAGE_SIZE_TABLE: z.number(),
});
