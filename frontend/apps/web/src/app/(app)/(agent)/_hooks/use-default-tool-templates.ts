'use client';

import { useQuery } from '@tanstack/react-query';

import { defaultToolTemplatesQueries } from '@/app/(app)/(agent)/_queries/default-tool-templates-query';

export function useDefaultToolTemplates() {
  return useQuery(defaultToolTemplatesQueries.list);
}
