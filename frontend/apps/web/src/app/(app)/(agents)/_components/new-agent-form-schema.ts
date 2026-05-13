import { z } from 'zod';

import { Platform } from '@/client/types.gen';

export const newAgentFormSchema = z
  .object({
    name: z.string().trim().min(1, 'Name is required').max(255),
    platform: z
      .enum([Platform.WEBHOOK, Platform.RETELL, Platform.VAPI, Platform.ELEVENLABS])
      .nullable(),
    integration_id: z.string().uuid().nullable(),
    platform_agent_id: z.string().nullable(),
    platform_agent_name: z.string().nullable(),
  })
  .refine((v) => v.platform !== null, {
    message: 'Platform is required',
    path: ['platform'],
  })
  .refine(
    (v) => {
      if (v.platform === Platform.WEBHOOK) {
        return v.integration_id === null && (v.platform_agent_id === null || v.platform_agent_id === '');
      }
      return true;
    },
    { message: 'Custom agents do not use integrations', path: ['integration_id'] }
  )
  .refine(
    (v) => {
      if (v.platform === null || v.platform === Platform.WEBHOOK) {
        return true;
      }
      return Boolean(v.integration_id && v.platform_agent_id && v.platform_agent_id.trim());
    },
    { message: 'Select integration and provider agent', path: ['platform_agent_id'] }
  );

export type NewAgentFormValues = z.infer<typeof newAgentFormSchema>;
