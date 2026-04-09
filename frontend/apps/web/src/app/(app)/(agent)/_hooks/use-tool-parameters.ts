'use client';

import { useFormContext, useFieldArray } from 'react-hook-form';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { makeDefaultParam } from '@/app/(app)/(agent)/_schemas/agent-form';

export function useToolParameters(toolIndex: number) {
  const { control } = useFormContext<AgentFormValues>();

  const { fields, append, remove } = useFieldArray({
    control,
    name: `tools.${toolIndex}.parameters`,
  });

  const addParameter = () => {
    append(makeDefaultParam());
  };

  return { fields, addParameter, remove };
}
