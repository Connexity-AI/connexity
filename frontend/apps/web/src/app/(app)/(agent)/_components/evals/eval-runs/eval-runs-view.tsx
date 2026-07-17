'use client';

import { useParams, useRouter } from 'next/navigation';

import { useEvalConfigs } from '@/app/(app)/(agent)/_hooks/use-eval-configs';
import { useEvalRuns } from '@/app/(app)/(agent)/_hooks/use-eval-runs';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import { EvalRunsList } from './eval-runs-list';

export function EvalRunsView() {
  const router = useRouter();
  const { agentId } = useParams<{ agentId: string }>();
  const { data: runsData } = useEvalRuns(agentId);
  const { data: configsData } = useEvalConfigs(agentId);

  const runs = runsData?.data ?? [];
  const configs = configsData?.data ?? [];

  return (
    <EvalRunsList
      agentId={agentId}
      runs={runs}
      configs={configs}
      onOpenRun={(runId) => router.push(UrlGenerator.agentEvalsRunDetail(agentId, runId))}
    />
  );
}
