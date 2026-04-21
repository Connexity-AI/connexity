'use client';

import { QueryClientProvider } from '@tanstack/react-query';

import getQueryClient from '@/lib/react-query/getQueryClient';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const QueryProvider: FC<Props> = ({ children }) => {
  const queryClient = getQueryClient();

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

export default QueryProvider;
