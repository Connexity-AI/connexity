import { getSttModels } from '@/actions/config';
import { sttModelKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';
import { EMPTY_SPEECH_MODELS } from '@/utils/empty-speech-models';

export const sttModelsQueries = {
  list: {
    queryKey: sttModelKeys.list(),
    queryFn: async () => {
      const catalog = await getSttModels();
      if (isSuccessApiResult(catalog)) {
        return catalog.data;
      }
      return EMPTY_SPEECH_MODELS;
    },
    staleTime: 5 * 60 * 1000,
  },
};
