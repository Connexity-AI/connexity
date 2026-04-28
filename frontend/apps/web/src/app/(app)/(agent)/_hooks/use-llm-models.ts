'use client';

import { useQuery } from '@tanstack/react-query';

import { llmModelsQuery } from '@/app/(app)/(agent)/_queries/llm-models-query';
import { FALLBACK_LLM_MODELS } from '@/constants/llm-models';

export function useLlmModels() {
  const query = useQuery(llmModelsQuery());

  return {
    ...query,
    data: query.data ?? FALLBACK_LLM_MODELS,
  };
}
