import { listAgentRuntimes } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function runtimesQuery(agentId: string) {
  return {
    queryKey: agentKeys.runtimes(agentId),
    queryFn: async () => {
      const result = await listAgentRuntimes(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch runtimes');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
