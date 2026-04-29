import { listTestCaseResultsByRun } from '@/actions/runs';
import { isSuccessApiResult } from '@/utils/api';
import { testCaseResultKeys } from '@/constants/query-keys';

export function testCaseResultsByRunQuery(runId: string) {
  return {
    queryKey: testCaseResultKeys.byRun(runId),

    queryFn: async () => {
      const result = await listTestCaseResultsByRun(runId);

      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch test case results');

      return result.data;
    },

    staleTime: 15 * 1000,
  };
}
