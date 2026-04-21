import { listEvalConfigs } from '@/actions/eval-configs';
import { evalConfigKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function evalConfigsListQuery(agentId: string) {
  return {
    queryKey: evalConfigKeys.list(agentId),
    queryFn: async () => {
      const result = await listEvalConfigs(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch eval configs');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
