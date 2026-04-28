import { getLlmModels } from '@/actions/config';
import { FALLBACK_LLM_MODELS } from '@/constants/llm-models';
import { llmModelKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function llmModelsQuery() {
  return {
    queryKey: llmModelKeys.list(),
    queryFn: async () => {
      const result = await getLlmModels();
      if (!isSuccessApiResult(result)) return FALLBACK_LLM_MODELS;
      return result.data;
    },
    staleTime: 5 * 60 * 1000,
  };
}
