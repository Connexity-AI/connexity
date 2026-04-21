import { listRuns } from '@/actions/runs';
import { isSuccessApiResult } from '@/utils/api';
import { runKeys } from '@/constants/query-keys';

export function evalRunsListQuery(agentId: string) {
  return {
    queryKey: runKeys.list(agentId),

    queryFn: async () => {
      const result = await listRuns(agentId);

      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch eval runs');

      return result.data;
    },

    staleTime: 15 * 1000,
  };
}
