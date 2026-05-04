'use server';

import { CustomMetricsService } from '@/client/sdk.gen';

import type {
  CustomMetricCreate,
  CustomMetricPublic,
  CustomMetricsPublic,
  CustomMetricUpdate,
  Message,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const listCustomMetrics = async (
  skip = 0,
  limit = 100
): Promise<ApiResult<CustomMetricsPublic>> => {
  const apiResponse = await CustomMetricsService.customMetricsListCustomMetrics({
    query: { skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const createCustomMetric = async (
  body: CustomMetricCreate
): Promise<ApiResult<CustomMetricPublic>> => {
  const apiResponse = await CustomMetricsService.customMetricsCreateCustomMetric({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const updateCustomMetric = async (
  metricId: string,
  body: CustomMetricUpdate
): Promise<ApiResult<CustomMetricPublic>> => {
  const apiResponse = await CustomMetricsService.customMetricsUpdateCustomMetric({
    path: { metric_id: metricId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const deleteCustomMetric = async (
  metricId: string
): Promise<ApiResult<Message>> => {
  const apiResponse = await CustomMetricsService.customMetricsDeleteCustomMetric({
    path: { metric_id: metricId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
