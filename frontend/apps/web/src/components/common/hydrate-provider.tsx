'use client';

import { HydrationBoundary } from '@tanstack/react-query';

import type { HydrationBoundaryProps } from '@tanstack/react-query';

export const HydrateProvider = (props: HydrationBoundaryProps) => {
  return <HydrationBoundary {...props} />;
};
