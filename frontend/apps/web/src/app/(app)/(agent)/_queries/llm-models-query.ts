import { getLlmModels } from '@/actions/config';
import { appConfigQueries } from '@/app/(app)/(agent)/_queries/app-config-query';
import { appConfigKeys, llmModelKeys } from '@/constants/query-keys';
import getQueryClient from '@/lib/react-query/getQueryClient';
import { isSuccessApiResult } from '@/utils/api';
import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  minimalLlmModelsFromRoute,
} from '@/utils/split-default-llm-routing';

import type { ConfigPublic } from '@/client/types.gen';

async function defaultLlmRouteForFallbackCatalog(): Promise<string> {
  const queryClient = getQueryClient();
  const cached = queryClient.getQueryData<ConfigPublic>(appConfigKeys.root());
  if (cached?.default_llm_model) {
    return cached.default_llm_model;
  }
  try {
    const config = await queryClient.ensureQueryData(appConfigQueries.root);
    return config.default_llm_model ?? BOOTSTRAP_DEFAULT_LLM_ROUTE;
  } catch {
    return BOOTSTRAP_DEFAULT_LLM_ROUTE;
  }
}

export const llmModelsQueries = {
  list: {
    queryKey: llmModelKeys.list(),
    queryFn: async () => {
      const route = await defaultLlmRouteForFallbackCatalog();

      const catalog = await getLlmModels();
      if (isSuccessApiResult(catalog)) {
        return catalog.data;
      }
      return minimalLlmModelsFromRoute(route);
    },
    staleTime: 5 * 60 * 1000,
  },
};
