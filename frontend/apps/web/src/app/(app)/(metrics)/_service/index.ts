import { listCustomMetrics } from '@/actions/custom-metrics';
import { customMetricKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export const CustomMetricService = {
  getCustomMetricsQuery: () => ({
    queryKey: customMetricKeys.list(),
    queryFn: async () => {
      const result = await listCustomMetrics();
      if (!isSuccessApiResult(result)) {
        throw new Error('Failed to fetch custom metrics');
      }
      return result.data;
    },
  }),
};
