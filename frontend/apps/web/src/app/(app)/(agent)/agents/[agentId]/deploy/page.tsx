import { Suspense } from 'react';

import { listIntegrations } from '@/actions/integrations';
import { isSuccessApiResult } from '@/utils/api';

import {
  EnvironmentsSection,
  EnvironmentsSectionSkeleton,
} from './_components/environments-section';

import type { IntegrationPublic } from '@/client/types.gen';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function AgentDeployPage({ params }: Props) {
  const { agentId } = await params;

  const result = await listIntegrations();
  const integrations: IntegrationPublic[] = isSuccessApiResult(result) ? result.data.data : [];

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        <Suspense fallback={<EnvironmentsSectionSkeleton />}>
          <EnvironmentsSection agentId={agentId} integrations={integrations} />
        </Suspense>
      </div>
    </div>
  );
}
