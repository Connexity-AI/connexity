'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { availableMetricsQuery } from '@/app/(app)/(agent)/_queries/available-metrics-query';

export function useAvailableMetrics() {
  return useSuspenseQuery(availableMetricsQuery());
}
