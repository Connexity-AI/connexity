import { listTestCases } from '@/actions/test-cases';
import { testCaseKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function testCasesListQuery(agentId: string, options?: { includeDeleted?: boolean }) {
  const includeDeleted = options?.includeDeleted === true;
  return {
    queryKey: includeDeleted
      ? testCaseKeys.listWithDeleted(agentId)
      : testCaseKeys.list(agentId),
    queryFn: async () => {
      const result = await listTestCases(agentId, 0, 100, { includeDeleted });
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch test cases');
      return result.data;
    },
    staleTime: 30 * 1000,
  };
}
