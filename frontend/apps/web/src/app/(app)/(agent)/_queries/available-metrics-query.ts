import { listAvailableMetrics } from '@/actions/eval-configs';
import { isSuccessApiResult } from '@/utils/api';
import { metricKeys } from '@/constants/query-keys';

export function availableMetricsQuery() {
  return {
    queryKey: metricKeys.list(),

    queryFn: async () => {
      const result = await listAvailableMetrics();
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch available metrics');
      return result.data;
    },
    staleTime: 5 * 60 * 1000,
  };
}
