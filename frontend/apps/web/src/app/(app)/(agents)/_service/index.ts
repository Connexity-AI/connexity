import { getAgents, type AgentFilters } from '@/actions/agents';

export class AgentService {
  static getAgentsQuery(filters: AgentFilters = {}) {
    return {
      queryKey: ['agents', filters],
      queryFn: () => getAgents(filters),
      staleTime: 30 * 1000,
    };
  }
}
