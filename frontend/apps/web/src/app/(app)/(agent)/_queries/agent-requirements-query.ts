import { getAgentRequirements } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';
import { agentKeys } from '@/constants/query-keys';

export function agentRequirementsQuery(agentId: string) {
  return {
    queryKey: agentKeys.requirements(agentId),
    queryFn: async () => {
      const result = await getAgentRequirements(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch requirements');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
