'use client';

import { useFormContext, useFieldArray } from 'react-hook-form';

import type { AgentFormValues, HttpMethod } from '@/app/(app)/(agent)/_schemas/agent-form';
import { makeDefaultAuthHeader } from '@/app/(app)/(agent)/_schemas/agent-form';

export function useToolEditor(toolIndex: number) {
  const { register, watch, setValue, control } = useFormContext<AgentFormValues>();

  const toolName = watch(`tools.${toolIndex}.name`);
  const method = watch(`tools.${toolIndex}.method`);

  const {
    fields: authFields,
    append: appendAuth,
    remove: removeAuth,
  } = useFieldArray({
    control,
    name: `tools.${toolIndex}.authHeaders`,
  });

  const setMethod = (value: HttpMethod) => {
    setValue(`tools.${toolIndex}.method`, value, { shouldDirty: true });
  };

  const setToolName = (value: string) => {
    setValue(`tools.${toolIndex}.name`, value, { shouldDirty: true });
  };

  const addAuthHeader = () => {
    appendAuth(makeDefaultAuthHeader());
  };

  return {
    register,
    toolName,
    method,
    authFields,
    toolIndex,
    setMethod,
    setToolName,
    removeAuth,
    addAuthHeader,
  };
}
