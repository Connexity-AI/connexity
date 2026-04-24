'use client';

import { useCallback, useMemo } from 'react';

import { isSameDay } from 'date-fns';
import { useQueryStates } from 'nuqs';

import { useCalls, useRefreshCalls } from '@/app/(app)/(agent)/_hooks/use-calls';
import { callsObserveParser } from '@/common/url-generator/parsers';

import { getPresetRange, type DateRangeValue, type PresetId } from './date-range-picker-utils';

import type { CallPublic } from '@/client/types.gen';

interface UseObserveCallsResult {
  rows: CallPublic[];
  totalCount: number;
  isLoading: boolean;
  isFetching: boolean;
  dateRange: DateRangeValue;
  onDateRangeChange: (next: DateRangeValue) => void;
  onRefresh: () => void;
  isRefreshPending: boolean;
}

export function useObserveCalls(agentId: string): UseObserveCallsResult {
  const [params, setParams] = useQueryStates(callsObserveParser, { shallow: false });

  const dateRange = useMemo<DateRangeValue>(() => {
    if (params.preset === 'custom') {
      const from = params.from ? new Date(params.from) : undefined;
      const rawTo = params.to ? new Date(params.to) : undefined;
      const to = rawTo && isSameDay(rawTo, new Date()) ? new Date() : rawTo;
      return { preset: 'custom', range: { from, to } };
    }
    return {
      preset: params.preset as Exclude<PresetId, 'custom'>,
      range: getPresetRange(params.preset),
    };
  }, [params.preset, params.from, params.to]);

  const callsQuery = useCalls(agentId, {
    page: params.page,
    pageSize: params.pageSize,
    dateFrom: dateRange.range.from?.toISOString() ?? null,
    dateTo: dateRange.range.to?.toISOString() ?? null,
  });
  const refreshMutation = useRefreshCalls(agentId);

  const rows = useMemo(() => callsQuery.data?.rows ?? [], [callsQuery.data]);
  const totalCount = callsQuery.data?.totalCount ?? 0;

  const onDateRangeChange = useCallback(
    (next: DateRangeValue) => {
      if (next.preset === 'custom') {
        void setParams({
          preset: 'custom',
          from: next.range.from ? next.range.from.toISOString() : '',
          to: next.range.to ? next.range.to.toISOString() : '',
          page: 1,
        });
      } else {
        void setParams({
          preset: next.preset,
          from: '',
          to: '',
          page: 1,
        });
      }
    },
    [setParams],
  );

  const onRefresh = useCallback(() => refreshMutation.mutate(), [refreshMutation]);

  return {
    rows,
    totalCount,
    isLoading: callsQuery.isLoading,
    isFetching: callsQuery.isFetching,
    dateRange,
    onDateRangeChange,
    onRefresh,
    isRefreshPending: refreshMutation.isPending,
  };
}
