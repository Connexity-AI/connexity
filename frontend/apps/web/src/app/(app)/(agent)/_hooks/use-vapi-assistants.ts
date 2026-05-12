'use client';

import { useQuery } from '@tanstack/react-query';

import { listVapiAssistants } from '@/actions/integrations';
import { isSuccessApiResult } from '@/utils/api';
import { vapiAssistantKeys } from '@/constants/query-keys';

export function useVapiAssistants(integrationId: string | null) {
  return useQuery({
    queryKey: vapiAssistantKeys.byIntegration(integrationId ?? ''),

    enabled: !!integrationId,

    queryFn: async () => {
      const result = await listVapiAssistants(integrationId!);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch Vapi assistants');
      return result.data;
    },

    staleTime: 30 * 1000,
  });
}
