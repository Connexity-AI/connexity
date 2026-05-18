'use client';

import { useQuery } from '@tanstack/react-query';

import { getAgentDraft } from '@/actions/agents';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { agentKeys } from '@/constants/query-keys';

import type { ErrorResponse } from '@/client/types.gen';

export function useAgentDraft(agentId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: agentKeys.draft(agentId),

    queryFn: async () => {
      const result = await getAgentDraft(agentId);
      if (isErrorApiResult<ErrorResponse>(result) && result.error.status === 404) {
        return null;
      }
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent draft');
      return result.data;
    },

    staleTime: 30 * 1000,
    enabled,
  });
}
