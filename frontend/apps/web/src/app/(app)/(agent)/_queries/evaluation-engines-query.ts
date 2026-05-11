import { listAgentEvaluationEngines } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function evaluationEnginesQuery(agentId: string) {
  return {
    queryKey: agentKeys.evaluationEngines(agentId),
    queryFn: async () => {
      const result = await listAgentEvaluationEngines(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch evaluation engines');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
