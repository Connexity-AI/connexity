import { listTestCases } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function testCasesListQuery(agentId: string) {
  return {
    queryKey: testCaseKeys.list(agentId),
    queryFn: async () => {
      const result = await listTestCases(agentId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch test cases');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
