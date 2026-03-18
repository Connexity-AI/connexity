import type { configClientSchema, processEnvSchema } from '@/schemas/config';
import type { z } from 'zod';

// Types for env and static config
export type ProcessEnvSchemaType = typeof processEnvSchema;
export type ProcessEnvType = z.infer<ProcessEnvSchemaType>;

export type ConfigClientSchemaType = typeof configClientSchema;
export type ConfigClientType = z.infer<ConfigClientSchemaType>;
