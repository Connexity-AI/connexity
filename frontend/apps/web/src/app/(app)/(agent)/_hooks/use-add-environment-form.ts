'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useCreateEnvironment } from '@/app/(app)/(agent)/_hooks/use-create-environment';
import { useEnvironmentPayloadPreview } from '@/app/(app)/(agent)/_hooks/use-environment-payload-preview';
import { useUpdateEnvironment } from '@/app/(app)/(agent)/_hooks/use-update-environment';
import { addEnvironmentFormSchema } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import type { AgentCanonicalDeployTarget } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/agent-canonical-deploy-target';
import {
  getAgentEnvironmentFormMode,
  type AgentEnvironmentFormMode,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/agent-environment-form-mode';
import {
  getEnvironmentCreateBody,
  getEnvironmentFormValues,
  getEnvironmentUpdateBody,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/environment-form-values';
import { isIntegrationPlatform } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/environment-platform-utils';

import type {
  AddEnvironmentFormInputValues,
  AddEnvironmentFormValues,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import type { EnvironmentPublic } from '@/client/types.gen';

interface UseAddEnvironmentFormOptions {
  agentId: string;
  environment: EnvironmentPublic | null;
  onSuccess: () => void;
}

export function useAddEnvironmentForm({
  agentId,
  environment,
  onSuccess,
}: UseAddEnvironmentFormOptions) {
  const { data: agent, isLoading: isAgentLoading } = useAgent(agentId);
  const agentTarget = agent as AgentCanonicalDeployTarget | undefined;
  const agentEnvironmentFormMode: AgentEnvironmentFormMode = getAgentEnvironmentFormMode(
    agentTarget,
    isAgentLoading
  );

  const createEnvironment = useCreateEnvironment(agentId);
  const updateEnvironment = useUpdateEnvironment(agentId);

  const form = useForm<AddEnvironmentFormInputValues, unknown, AddEnvironmentFormValues>({
    resolver: zodResolver(addEnvironmentFormSchema),
    defaultValues: getEnvironmentFormValues(environment, agentTarget),
    values: getEnvironmentFormValues(environment, agentTarget),
  });

  const name = form.watch('name');
  const platform = form.watch('platform');
  const evalGateEnabled = form.watch('eval_gate_enabled');
  const evalGateEvalConfigId = form.watch('eval_gate_eval_config_id');
  const isPending = createEnvironment.isPending || updateEnvironment.isPending;
  const error = createEnvironment.error ?? updateEnvironment.error;
  const integrationPlatform = isIntegrationPlatform(platform) ? platform : null;
  const isEditing = environment !== null;
  const submitLabel = isEditing ? 'Save changes' : 'Add environment';
  const needsAgentForNewEnvironment = environment === null && agentEnvironmentFormMode === 'loading';
  const isSubmitDisabled =
    isPending ||
    needsAgentForNewEnvironment ||
    (evalGateEnabled && evalGateEvalConfigId == null);
  const environmentNameForPreview = name.trim() || 'production';
  const payloadPreview = useEnvironmentPayloadPreview({
    agentId,
    platform,
    environmentName: environmentNameForPreview,
    evalGateEnabled,
    evalGateEvalConfigId: evalGateEvalConfigId ?? null,
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      if (environment === null) {
        await createEnvironment.mutateAsync(getEnvironmentCreateBody(values, agentId));
      } else {
        await updateEnvironment.mutateAsync({
          environmentId: environment.id,
          body: getEnvironmentUpdateBody(values),
        });
      }
      onSuccess();
    } catch {
      // error surfaced via `error` and rendered by the form.
    }
  });

  return {
    form,
    onSubmit,
    platform,
    integrationPlatform,
    payloadOpen: payloadPreview.payloadOpen,
    onTogglePayloadOpen: payloadPreview.onTogglePayloadOpen,
    payloadPreview: payloadPreview.payloadPreview,
    isPayloadPreviewLoading: payloadPreview.isPayloadPreviewLoading,
    showMissingPublishedVersionInfo: payloadPreview.showMissingPublishedVersionInfo,
    submitLabel,
    isSubmitDisabled,
    isPending,
    error,
    agentEnvironmentFormMode,
    agentTarget,
  };
}
