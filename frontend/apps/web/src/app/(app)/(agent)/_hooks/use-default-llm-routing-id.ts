'use client';

import { useQuery } from '@tanstack/react-query';

import { appConfigQueries } from '@/app/(app)/(agent)/_queries/app-config-query';
import { BOOTSTRAP_DEFAULT_LLM_ROUTE } from '@/utils/split-default-llm-routing';

export function useDefaultLlmRoutingId(): string {
  const { data } = useQuery(appConfigQueries.root);
  return data?.default_llm_model ?? BOOTSTRAP_DEFAULT_LLM_ROUTE;
}
