import { z } from 'zod';

import type { ZodError, ZodType } from 'zod';

export const formatZodError = (error: ZodError, multiLine = false): string => {
  const listBullet = multiLine ? '- ' : '';
  const separator = multiLine ? '\n' : ', ';

  const issues = error.issues.map((issue) => {
    const variable = issue.path.join('.') || 'configuration';
    return `${listBullet}Invalid variable [${variable}]: ${issue.message}`;
  });

  return issues.join(separator);
};

export const validateData = <T extends ZodType>(config: z.infer<T>, schema: T): z.infer<T> => {
  const parsedConfig = schema.safeParse(config);

  if (!parsedConfig.success) {
    const zodErrors = formatZodError(parsedConfig.error);
    const errorMessage = `Zod validation failed: , ${zodErrors}`;

    console.error(errorMessage);
    throw new Error(errorMessage);
  }

  const { data: parsedConfigData } = parsedConfig;

  return parsedConfigData;
};
