import { getAgentVersions } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';
import { agentKeys } from '@/constants/query-keys';

export function agentVersionsListQuery(agentId: string) {
  return {
    queryKey: agentKeys.versions(agentId),

    queryFn: async () => {
      const result = await getAgentVersions(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch agent versions');
      return result.data;
    },

    staleTime: 30 * 1000,
  };
}
