import { getTtsVoices } from '@/actions/config';
import { ttsVoiceKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

import type { VoicesPublic } from '@/client/types.gen';

const EMPTY_VOICES: VoicesPublic = {
  data: [],
  count: 0,
  default_voice_id: null,
};

export function ttsVoicesQuery(provider: string, model: string) {
  return {
    queryKey: ttsVoiceKeys.list(provider, model),
    queryFn: async () => {
      const result = await getTtsVoices(provider, model);
      if (isSuccessApiResult(result)) {
        return result.data;
      }
      return EMPTY_VOICES;
    },
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(provider.trim() && model.trim()),
  };
}
