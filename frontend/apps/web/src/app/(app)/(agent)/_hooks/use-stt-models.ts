'use client';

import { useQuery } from '@tanstack/react-query';

import { sttModelsQueries } from '@/app/(app)/(agent)/_queries/stt-models-query';
import { EMPTY_SPEECH_MODELS } from '@/utils/empty-speech-models';

export function useSttModels() {
  const query = useQuery(sttModelsQueries.list);
  return {
    ...query,
    data: query.data ?? EMPTY_SPEECH_MODELS,
  };
}
