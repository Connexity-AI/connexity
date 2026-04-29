import { EvalsTabs } from '@/app/(app)/(agent)/_components/evals/evals-tabs';

import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  params: Promise<{ agentId: string }>;
}

export default async function EvalsLayout({ children, params }: Props) {
  const { agentId } = await params;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <EvalsTabs agentId={agentId} />
      {children}
    </div>
  );
}
