import { NewAgentHeader } from '@/app/(app)/(agents)/_components/new-agent-header';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const AgentsLayout: FC<Props> = ({ children }) => (
  <>
    <NewAgentHeader />

    <main className="flex-1">{children}</main>
  </>
);

export default AgentsLayout;
