'use client';

import { CreateEvalView } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-view';
import { useEvalConfigDetail } from '@/app/(app)/(agent)/_hooks/use-eval-config-detail';

interface EvalConfigDetailViewProps {
  agentId: string;
  evalConfigId: string;
}

export function EvalConfigDetailView({ agentId, evalConfigId }: EvalConfigDetailViewProps) {
  const { data } = useEvalConfigDetail(evalConfigId);

  return (
    <CreateEvalView
      agentId={agentId}
      readOnly
      initialConfig={data.config}
      initialMembers={data.members}
    />
  );
}
