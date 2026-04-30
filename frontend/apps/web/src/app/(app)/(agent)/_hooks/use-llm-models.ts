'use client';

import { useQuery } from '@tanstack/react-query';

import { llmModelsQueries } from '@/app/(app)/(agent)/_queries/llm-models-query';
import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  minimalLlmModelsFromRoute,
} from '@/utils/split-default-llm-routing';

export function useLlmModels() {
  const query = useQuery(llmModelsQueries.list);

  return {
    ...query,
    data:
      query.data ?? minimalLlmModelsFromRoute(BOOTSTRAP_DEFAULT_LLM_ROUTE),
  };
}
