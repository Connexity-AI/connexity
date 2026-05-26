'use client';

import { useQuery } from '@tanstack/react-query';

import { ttsVoicesQuery } from '@/app/(app)/(agent)/_queries/tts-voices-query';

import type { VoicesPublic } from '@/client/types.gen';

const EMPTY_VOICES: VoicesPublic = {
  data: [],
  count: 0,
  default_voice_id: null,
};

export function useTtsVoices(provider: string, model: string) {
  const query = useQuery(ttsVoicesQuery(provider, model));
  return {
    ...query,
    data: query.data ?? EMPTY_VOICES,
  };
}
