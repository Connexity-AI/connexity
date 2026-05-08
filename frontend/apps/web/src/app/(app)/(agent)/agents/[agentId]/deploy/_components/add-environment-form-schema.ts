import { z } from 'zod';

export const addEnvironmentFormSchema = z
  .object({
    name: z.string().trim().min(1, 'Name is required').max(255),
    platform: z.enum(['retell', 'vapi', 'webhook']),
    integration_id: z.string().uuid('Select an integration').nullable(),
    platform_agent_id: z.string().nullable(),
    platform_agent_name: z.string().nullable(),
    endpoint_url: z
      .string()
      .trim()
      .url('Enter a valid URL')
      .regex(/^https?:\/\//i, 'URL must start with http:// or https://')
      .nullable(),
    eval_gate_enabled: z.boolean(),
    eval_gate_eval_config_id: z.string().uuid().nullable(),
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
      if (v.platform === 'retell' || v.platform === 'vapi') {
        return Boolean(v.integration_id && v.platform_agent_id);
      }
      return true;
    },
    {
      message: 'Select integration and agent',
      path: ['platform_agent_id'],
    }
  )
  .refine(
    (v) => {
      if (v.platform === 'webhook') {
        return Boolean(v.endpoint_url);
      }
      return true;
    },
    {
      message: 'Enter a webhook URL',
      path: ['endpoint_url'],
    }
  );

export type AddEnvironmentFormValues = z.infer<typeof addEnvironmentFormSchema>;
