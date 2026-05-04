'use client';

import { useMutation, useQueryClient, useSuspenseQuery } from '@tanstack/react-query';

import { CustomMetricService } from '@/app/(app)/(metrics)/_service';
import {
  createCustomMetric,
  deleteCustomMetric,
  updateCustomMetric,
} from '@/actions/custom-metrics';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { customMetricKeys, metricKeys } from '@/constants/query-keys';

import type {
  CustomMetricCreate,
  CustomMetricPublic,
  CustomMetricUpdate,
  CustomMetricsPublic,
} from '@/client/types.gen';

export function useCustomMetrics() {
  return useSuspenseQuery(CustomMetricService.getCustomMetricsQuery());
}

export function useCreateCustomMetric() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (body: CustomMetricCreate) => {
      const result = await createCustomMetric(body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },

    onMutate: async (body) => {
      const listKey = customMetricKeys.list();
      await queryClient.cancelQueries({ queryKey: listKey });
      const previous = queryClient.getQueryData<CustomMetricsPublic>(listKey);

      const now = new Date().toISOString();
      const optimistic: CustomMetricPublic = {
        id: `optimistic-${crypto.randomUUID()}`,
        name: body.name,
        display_name: body.display_name,
        description: body.description,
        tier: body.tier,
        default_weight: body.default_weight ?? 1.0,
        score_type: body.score_type,
        rubric: body.rubric,
        include_in_defaults: body.include_in_defaults ?? false,
        is_predefined: false,
        is_draft: body.is_draft ?? false,
        created_by: null,
        created_at: now,
        updated_at: now,
      };

      queryClient.setQueryData<CustomMetricsPublic>(listKey, (current) =>
        current
          ? { ...current, data: [...current.data, optimistic], count: current.count + 1 }
          : { data: [optimistic], count: 1 }
      );

      return { previous };
    },

    onError: (_err, _body, context) => {
      if (context?.previous) {
        queryClient.setQueryData(customMetricKeys.list(), context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: customMetricKeys.all });
      // The create-eval judge picker reads /config/available-metrics, which
      // mirrors the same active set; keep it in sync after any mutation.
      void queryClient.invalidateQueries({ queryKey: metricKeys.list() });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}

export function useUpdateCustomMetric() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ metricId, body }: { metricId: string; body: CustomMetricUpdate }) => {
      const result = await updateCustomMetric(metricId, body);

      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },

    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: customMetricKeys.all });
      // The create-eval judge picker reads /config/available-metrics, which
      // mirrors the same active set; keep it in sync after any mutation.
      void queryClient.invalidateQueries({ queryKey: metricKeys.list() });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}

export function useDeleteCustomMetric() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (metricId: string) => {
      const result = await deleteCustomMetric(metricId);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },

    onMutate: async (metricId) => {
      const listKey = customMetricKeys.list();
      await queryClient.cancelQueries({ queryKey: listKey });
      const previous = queryClient.getQueryData<CustomMetricsPublic>(listKey);

      queryClient.setQueryData<CustomMetricsPublic>(listKey, (current) => {
        if (!current) return current;
        const next = current.data.filter((m) => m.id !== metricId);
        return { ...current, data: next, count: Math.max(0, current.count - 1) };
      });

      return { previous };
    },

    onError: (_err, _metricId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(customMetricKeys.list(), context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: customMetricKeys.all });
      // The create-eval judge picker reads /config/available-metrics, which
      // mirrors the same active set; keep it in sync after any mutation.
      void queryClient.invalidateQueries({ queryKey: metricKeys.list() });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
