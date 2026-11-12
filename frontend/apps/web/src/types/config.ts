import type { processEnvSchema } from '@/schemas/config';
import type { z } from 'zod';

// Types for env and static config
export type ProcessEnvSchemaType = typeof processEnvSchema;
export type ProcessEnvType = z.infer<ProcessEnvSchemaType>;
