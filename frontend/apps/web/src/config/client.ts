import { configClientSchema } from '@/schemas/config';
import { validateData } from '@/utils/validation';

import type { ConfigClientType } from '@/types/config';

/**
 * Not set in .env.* files, hardcoded constants in source.
 * Same for all environments.
 */
const configClientData: ConfigClientType = {
  PAGE_SIZE_TABLE: 5,
};

export const CONFIG_CLIENT = validateData(configClientData, configClientSchema);
