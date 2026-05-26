'use client';

import { useQuery } from '@tanstack/react-query';

import { listElevenlabsAgents } from '@/actions/integrations';
import { elevenlabsAgentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useElevenlabsAgents(integrationId: string | null) {
  return useQuery({
    queryKey: elevenlabsAgentKeys.byIntegration(integrationId ?? ''),
    enabled: !!integrationId,
    queryFn: async () => {
      const result = await listElevenlabsAgents(integrationId!);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch ElevenLabs agents');
      return result.data;
    },
    staleTime: 30 * 1000,
  });
}
