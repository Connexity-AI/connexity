import { getAgentFlowStaleness } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';
import { agentKeys } from '@/constants/query-keys';

export function agentFlowStalenessQuery(agentId: string) {
  return {
    queryKey: agentKeys.flowStaleness(agentId),
    queryFn: async () => {
      const result = await getAgentFlowStaleness(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to check flow staleness');
      return result.data;
    },
    // Checked once per browser session per agent: a Retell edit is infrequent,
    // manual work done in Retell's UI, not something that needs live polling.
    // A hard page reload naturally re-triggers the check.
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  };
}
