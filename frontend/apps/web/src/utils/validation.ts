import { z } from 'zod';

import type { ZodError, ZodType } from 'zod';

/** ITU-T E.164: leading +, country code 1–9, up to 15 digits total. */
export const E164_PHONE_REGEX = /^\+[1-9]\d{1,14}$/;

export const E164_PHONE_MESSAGE =
  'Enter a valid E.164 phone number (e.g. +15551234567)';

/** Strip common formatting; does not add a leading +. */
export function normalizePhoneNumber(value: string): string {
  return value.trim().replace(/[\s\-().]/g, '');
}

export function isValidE164Phone(value: string): boolean {
  return E164_PHONE_REGEX.test(normalizePhoneNumber(value));
}

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
