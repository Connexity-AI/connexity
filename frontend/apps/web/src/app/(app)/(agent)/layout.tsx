import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const AgentLayout: FC<Props> = ({ children }) => (
  <main className="h-screen flex flex-col overflow-hidden">{children}</main>
);

export default AgentLayout;
