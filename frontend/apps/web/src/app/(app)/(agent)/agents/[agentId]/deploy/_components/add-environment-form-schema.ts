import { z } from 'zod';

export const addEnvironmentFormSchema = z
  .object({
    name: z.string().trim().min(1, 'Name is required').max(255),
    platform: z.enum(['retell']),
    integration_id: z.string().uuid('Select an integration'),
    platform_agent_id: z.string().min(1, 'Select an agent'),
    platform_agent_name: z.string(),
    eval_gate_enabled: z.boolean(),
    eval_gate_eval_config_id: z.string().uuid().nullable(),
  })
  .refine(
    (v) => !v.eval_gate_enabled || v.eval_gate_eval_config_id !== null,
    {
      message: 'Select an eval config for the gate',
      path: ['eval_gate_eval_config_id'],
    }
  );

export type AddEnvironmentFormValues = z.infer<typeof addEnvironmentFormSchema>;
