'use client';

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import NavLink from '@/components/shell/nav-link';
import { WORK_WAITING_KEY } from '@/components/work/work-query';

import type { FC, ReactNode } from 'react';

interface Props {
  title: string;
  url: string;
  icon: ReactNode;
  /** The layout's count, the first value; Work's reloads replace it. */
  waiting?: number;
}

/** The Work entry: its warm count follows Work's reloads with no request of its own. */
export const WorkNavLink: FC<Props> = ({ title, url, icon, waiting }) => {
  const queryClient = useQueryClient();
  // A new count from the layout (after a move or an answer) wins too.
  useEffect(() => {
    if (waiting !== undefined) queryClient.setQueryData(WORK_WAITING_KEY, waiting);
  }, [queryClient, waiting]);
  const { data } = useQuery({
    queryKey: WORK_WAITING_KEY,
    queryFn: () => waiting ?? 0,
    initialData: waiting ?? 0,
    staleTime: Infinity,
    enabled: false,
  });
  return <NavLink title={title} url={url} icon={icon} count={data || undefined} warm />;
};
