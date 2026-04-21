'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { evalConfigDetailQuery } from '@/app/(app)/(agent)/_queries/eval-config-detail-query';

export function useEvalConfigDetail(evalConfigId: string) {
  return useSuspenseQuery(evalConfigDetailQuery(evalConfigId));
}
