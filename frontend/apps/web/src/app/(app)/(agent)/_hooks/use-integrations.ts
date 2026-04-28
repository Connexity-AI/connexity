'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { integrationsListQuery } from '@/app/(app)/(agent)/_queries/integrations-list-query';

export function useIntegrations() {
  return useSuspenseQuery(integrationsListQuery());
}
