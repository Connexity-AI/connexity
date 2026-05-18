'use client';

import { useState } from 'react';

import { useQuery } from '@tanstack/react-query';

import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { webhookPayloadPreviewQuery } from '@/app/(app)/(agent)/_queries/webhook-payload-preview-query';
import { Platform } from '@/client/types.gen';

import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';

interface UseEnvironmentPayloadPreviewOptions {
  agentId: string;
  platform: AddEnvironmentFormValues['platform'];
  environmentName: string;
  evalGateEvalConfigId: string | null;
  evalGateEnabled: boolean;
}

export function useEnvironmentPayloadPreview({
  agentId,
  platform,
  environmentName,
  evalGateEvalConfigId,
  evalGateEnabled,
}: UseEnvironmentPayloadPreviewOptions) {
  const [payloadOpen, setPayloadOpen] = useState(false);
  const { data: agentVersionsData, isLoading: isAgentVersionsLoading } = useAgentVersions(agentId);
  const hasPublishedAgentVersion =
    (agentVersionsData?.count ?? agentVersionsData?.data.length ?? 0) > 0;
  const showMissingPublishedVersionInfo = !isAgentVersionsLoading && !hasPublishedAgentVersion;
  const {
    data: payloadPreviewData,
    isLoading: isPayloadPreviewLoading,
    isError: isPayloadPreviewError,
    error: payloadPreviewError,
  } = useQuery({
    ...webhookPayloadPreviewQuery({
      agentId,
      environmentName,
      evalGateEvalConfigId: evalGateEnabled ? evalGateEvalConfigId : null,
    }),
    enabled: platform === Platform.WEBHOOK && hasPublishedAgentVersion,
  });

  let payloadPreview = JSON.stringify(payloadPreviewData ?? {}, null, 2);
  if (isPayloadPreviewError) {
    payloadPreview = 'unable to load payload preview right now';
    if (payloadPreviewError instanceof Error) {
      payloadPreview = payloadPreviewError.message;
    }
  }

  return {
    payloadOpen,
    onTogglePayloadOpen: () => setPayloadOpen((open) => !open),
    payloadPreview,
    isPayloadPreviewLoading,
    showMissingPublishedVersionInfo,
  };
}
