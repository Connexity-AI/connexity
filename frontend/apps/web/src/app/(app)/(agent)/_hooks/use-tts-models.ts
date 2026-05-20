'use client';

import { useQuery } from '@tanstack/react-query';

import { ttsModelsQueries } from '@/app/(app)/(agent)/_queries/tts-models-query';
import { EMPTY_SPEECH_MODELS } from '@/utils/empty-speech-models';

export function useTtsModels() {
  const query = useQuery(ttsModelsQueries.list);
  return {
    ...query,
    data: query.data ?? EMPTY_SPEECH_MODELS,
  };
}
