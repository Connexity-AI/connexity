import { listAgentTools } from '@/actions/integrations';
import { integrationKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function agentToolsQuery(agentId: string) {
  return {
    queryKey: integrationKeys.agentTools(agentId),
    queryFn: async () => {
      const result = await listAgentTools(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch the agent\'s tools');
      return result.data;
    },
  };
}
