import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const AgentLayout: FC<Props> = ({ children }) => (
  <main className="flex-1 flex flex-col">{children}</main>
);

export default AgentLayout;
