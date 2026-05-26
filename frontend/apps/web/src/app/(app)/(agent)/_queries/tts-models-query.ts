import { getTtsModels } from '@/actions/config';
import { ttsModelKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';
import { EMPTY_SPEECH_MODELS } from '@/utils/empty-speech-models';

export const ttsModelsQueries = {
  list: {
    queryKey: ttsModelKeys.list(),
    queryFn: async () => {
      const catalog = await getTtsModels();
      if (isSuccessApiResult(catalog)) {
        return catalog.data;
      }
      return EMPTY_SPEECH_MODELS;
    },
    staleTime: 5 * 60 * 1000,
  },
};
