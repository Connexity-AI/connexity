import { z } from 'zod';

import { Platform } from '@/client/types.gen';

const optionalEmptyToNullInput = z.union([
  z.string(),
  z.literal(''),
  z.undefined(),
  z.null(),
]);

const nullableUuidString = optionalEmptyToNullInput
  .transform((value) => {
    if (value === '' || value === undefined || value === null) {
      return null;
    }
    return value;
  })
  .pipe(z.union([z.null(), z.string().uuid()]));

const nullableNonEmptyString = optionalEmptyToNullInput
  .transform((value) => {
    if (value === '' || value === undefined || value === null) {
      return null;
    }
    return value.trim();
  })
  .pipe(z.union([z.null(), z.string().min(1)]));

export const addEnvironmentFormSchema = z
  .object({
    name: z.string().trim().min(1, 'Name is required').max(255),
    platform: z.enum([Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS, Platform.WEBHOOK]),
    integration_id: nullableUuidString,
    platform_agent_id: nullableNonEmptyString,
    platform_agent_name: nullableNonEmptyString,
    endpoint_url: z
      .string()
      .trim()
      .url('Enter a valid URL')
      .regex(/^https?:\/\//i, 'URL must start with http:// or https://')
      .nullable(),
    eval_gate_enabled: z.boolean(),
    eval_gate_eval_config_id: nullableUuidString,
  })
  .refine(
    (v) => !v.eval_gate_enabled || v.eval_gate_eval_config_id !== null,
    {
      message: 'Select an eval config for the gate',
      path: ['eval_gate_eval_config_id'],
    }
  )
  .refine(
    (v) => {
      if (v.platform === Platform.WEBHOOK) {
        return Boolean(v.endpoint_url);
      }
      return true;
    },
    {
      message: 'Enter a webhook URL',
      path: ['endpoint_url'],
    }
  )
  .refine(
    (v) => {
      if (v.platform === Platform.WEBHOOK) {
        return true;
      }
      return v.integration_id !== null;
    },
    {
      message: 'Select an integration',
      path: ['integration_id'],
    }
  )
  .refine(
    (v) => {
      if (v.platform === Platform.WEBHOOK) {
        return true;
      }
      return v.platform_agent_id !== null;
    },
    {
      message: 'Select an agent',
      path: ['platform_agent_id'],
    }
  );

export type AddEnvironmentFormValues = z.output<typeof addEnvironmentFormSchema>;
export type AddEnvironmentFormInputValues = z.input<typeof addEnvironmentFormSchema>;
