import { MetricsHeader } from '@/app/(app)/(metrics)/_components/metrics-header';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const MetricsLayout: FC<Props> = ({ children }) => (
  <>
    <MetricsHeader />

    <main className="flex-1 min-h-0">{children}</main>
  </>
);

export default MetricsLayout;
