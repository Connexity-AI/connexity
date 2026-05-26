import { getAgent } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';
import { agentKeys } from '@/constants/query-keys';

export const agentDetailQuery = (agentId: string) => ({
  queryKey: agentKeys.detail(agentId),

  queryFn: async () => {
    const result = await getAgent(agentId);

    if (!isSuccessApiResult(result)) {
      throw new Error('Failed to fetch agent');
    }

    return result.data;
  },

  staleTime: 30_000,
});
