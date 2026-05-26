'use client';

import { useEffect, useMemo, useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import { useFormContext } from 'react-hook-form';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import { useTestRuntime } from '@/app/(app)/(agent)/_hooks/use-test-runtime';
import { runtimesQuery } from '@/app/(app)/(agent)/_queries/runtimes-query';
import { runtimeConfigForKind } from '@/app/(app)/(agent)/_utils/runtime-field-helpers';
import { TextRuntimeKind } from '@/client/types.gen';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { TextRuntimeKind as TextRuntimeKindType } from '@/client/types.gen';

interface UseRuntimeFieldArgs {
  agentId: string;
  defaultToBackendOption: boolean;
}

function normalizeTestMessage(message: unknown, fallback: string): string {
  if (typeof message !== 'string') {
    return fallback;
  }
  const normalized = message.trim();
  const lowered = normalized.toLowerCase();
  if (
    !normalized ||
    lowered === 'undefined' ||
    lowered === 'null' ||
    lowered.includes('undefined') ||
    lowered.includes('null') ||
    lowered === 'network error:' ||
    lowered === 'network error'
  ) {
    return fallback;
  }
  return normalized;
}

export function useRuntimeField({
  agentId,
  defaultToBackendOption,
}: UseRuntimeFieldArgs) {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const { data, isLoading, error } = useQuery(runtimesQuery(agentId));
  const [defaultApplied, setDefaultApplied] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const testRuntime = useTestRuntime();

  const selectedRuntime = form.watch('run.runtime');
  const runtimeOptions = useMemo(() => {
    const options = data?.data ?? [];
    const seen = new Set<string>();
    return options.filter((option) => {
      if (seen.has(option.kind)) {
        return false;
      }
      seen.add(option.kind);
      return true;
    });
  }, [data?.data]);
  const selectedKind = selectedRuntime.kind;
  const customEndpointUrl =
    selectedRuntime.kind === TextRuntimeKind.CUSTOM_ENDPOINT ? selectedRuntime.url : '';

  useEffect(() => {
    if (runtimeOptions.length === 0) {
      return;
    }

    const selectedAvailable = runtimeOptions.some((option) => option.kind === selectedKind);
    if (selectedAvailable) {
      return;
    }

    const fallback = runtimeOptions.find((option) => option.is_default) ?? runtimeOptions[0];
    if (!fallback) {
      return;
    }

    form.setValue('run.runtime', runtimeConfigForKind(fallback.kind), {
      shouldDirty: true,
      shouldValidate: true,
    });
  }, [runtimeOptions, form, selectedKind]);

  useEffect(() => {
    if (defaultApplied || !defaultToBackendOption || runtimeOptions.length === 0) {
      return;
    }

    const defaultOption = runtimeOptions.find((option) => option.is_default) ?? runtimeOptions[0];
    if (!defaultOption) {
      return;
    }

    if (selectedKind === TextRuntimeKind.CONNEXITY && defaultOption.kind !== selectedKind) {
      form.setValue('run.runtime', runtimeConfigForKind(defaultOption.kind), {
        shouldDirty: false,
        shouldValidate: true,
      });
    }

    setDefaultApplied(true);
  }, [defaultApplied, defaultToBackendOption, runtimeOptions, form, selectedKind]);

  const selectRuntime = (kind: TextRuntimeKindType) => {
    if (readOnly) {
      return;
    }

    const nextUrl = kind === TextRuntimeKind.CUSTOM_ENDPOINT ? customEndpointUrl : '';
    form.setValue('run.runtime', runtimeConfigForKind(kind, nextUrl), {
      shouldDirty: true,
      shouldValidate: false,
    });
    form.setValue(
      'run.runtime_test',
      { ok: false, url: null },
      {
        shouldDirty: true,
        shouldValidate: false,
      }
    );
    setTestResult(null);
  };

  const setCustomEndpointUrl = (url: string) => {
    form.setValue(
      'run.runtime',
      { kind: TextRuntimeKind.CUSTOM_ENDPOINT, url },
      {
        shouldDirty: true,
        shouldValidate: false,
      }
    );
    form.setValue(
      'run.runtime_test',
      { ok: false, url: null },
      {
        shouldDirty: true,
        shouldValidate: false,
      }
    );
    setTestResult(null);
  };

  const testCustomEndpoint = async () => {
    const url = customEndpointUrl.trim();
    setTestResult(null);

    try {
      const result = await testRuntime.mutateAsync({
        agent_id: agentId,
        mode: 'text',
        runtime: { kind: TextRuntimeKind.CUSTOM_ENDPOINT, url },
      });

      setTestResult({
        ok: result.ok,
        message: normalizeTestMessage(
          result.message,
          result.ok ? 'URL responded successfully.' : 'URL test failed.'
        ),
      });
      form.setValue(
        'run.runtime_test',
        { ok: result.ok, url: result.ok ? url : null },
        {
          shouldDirty: true,
          shouldValidate: true,
        }
      );

      if (result.ok) {
        form.setValue(
          'run.runtime',
          { kind: TextRuntimeKind.CUSTOM_ENDPOINT, url },
          {
            shouldDirty: true,
            shouldValidate: true,
          }
        );
      }
    } catch (err) {
      const message = normalizeTestMessage(
        err instanceof Error ? err.message : null,
        'Failed to test URL. Please verify the endpoint is reachable.'
      );
      setTestResult({ ok: false, message });

      form.setValue(
        'run.runtime_test',
        { ok: false, url: null },
        {
          shouldDirty: true,
          shouldValidate: true,
        }
      );
    }
  };

  const testDisabled =
    readOnly ||
    testRuntime.isPending ||
    customEndpointUrl.trim().length === 0 ||
    (!customEndpointUrl.trim().startsWith('http://') &&
      !customEndpointUrl.trim().startsWith('https://'));

  return {
    form,
    readOnly,
    error,
    isLoading,
    runtimeOptions,
    selectedRuntime,
    customEndpointUrl,
    testResult,
    testRuntime,
    selectRuntime,
    setCustomEndpointUrl,
    testCustomEndpoint,
    testDisabled,
  };
}
