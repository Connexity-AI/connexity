import { getAgents, type AgentFilters } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';

export class AgentService {
  static getAgentsQuery(filters: AgentFilters = {}) {
    return {
      queryKey: agentKeys.list(filters),
      queryFn: () => getAgents(filters),
      staleTime: 30 * 1000,
    };
  }
}
