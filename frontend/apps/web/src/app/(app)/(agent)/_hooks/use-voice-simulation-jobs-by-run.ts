'use client';

import { useQuery } from '@tanstack/react-query';

import { voiceSimulationKeys } from '@/constants/query-keys';
import { VoiceSimulationsService } from '@/client/sdk.gen';

export function useVoiceSimulationJobsByRun(runId: string, enabled: boolean) {
  return useQuery({
    queryKey: voiceSimulationKeys.jobsByRun(runId),
    enabled,
    queryFn: async () => {
      const apiResponse =
        await VoiceSimulationsService.voiceSimulationsListVoiceSimulationJobsForRun({
          path: { run_id: runId },
        });
      if (apiResponse.error !== undefined) {
        throw new Error('Failed to fetch voice simulation jobs');
      }
      return apiResponse.data;
    },
    staleTime: 10_000,
  });
}
