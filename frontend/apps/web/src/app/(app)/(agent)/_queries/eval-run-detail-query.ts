import { getRun } from '@/actions/runs';
import { isSuccessApiResult } from '@/utils/api';
import { runKeys } from '@/constants/query-keys';

export function evalRunDetailQuery(runId: string) {
  return {
    queryKey: runKeys.detail(runId),

    queryFn: async () => {
      const result = await getRun(runId);

      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch eval run');

      return result.data;
    },
    staleTime: 15 * 1000,
  };
}
