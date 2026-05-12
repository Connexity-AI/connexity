'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { useCreateEnvironment } from '@/app/(app)/(agent)/_hooks/use-create-environment';
import { useEnvironmentPayloadPreview } from '@/app/(app)/(agent)/_hooks/use-environment-payload-preview';
import { useUpdateEnvironment } from '@/app/(app)/(agent)/_hooks/use-update-environment';
import { addEnvironmentFormSchema } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import {
  getEnvironmentCreateBody,
  getEnvironmentFormValues,
  getEnvironmentUpdateBody,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/environment-form-values';
import {
  getAgentLabel,
  getIntegrationEmptyLabel,
  isIntegrationPlatform,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/environment-platform-utils';

import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import type { EnvironmentPublic, IntegrationPublic } from '@/client/types.gen';

interface UseAddEnvironmentFormOptions {
  agentId: string;
  integrations: IntegrationPublic[];
  environment: EnvironmentPublic | null;
  onSuccess: () => void;
}

export function useAddEnvironmentForm({
  agentId,
  integrations,
  environment,
  onSuccess,
}: UseAddEnvironmentFormOptions) {
  const createEnvironment = useCreateEnvironment(agentId);
  const updateEnvironment = useUpdateEnvironment(agentId);

  const form = useForm<AddEnvironmentFormValues>({
    resolver: zodResolver(addEnvironmentFormSchema),
    defaultValues: getEnvironmentFormValues(environment),
    values: getEnvironmentFormValues(environment),
  });

  const name = form.watch('name');
  const integrationId = form.watch('integration_id');
  const platform = form.watch('platform');
  const evalGateEnabled = form.watch('eval_gate_enabled');
  const evalGateEvalConfigId = form.watch('eval_gate_eval_config_id');
  const isPending = createEnvironment.isPending || updateEnvironment.isPending;
  const error = createEnvironment.error ?? updateEnvironment.error;
  const integrationPlatform = isIntegrationPlatform(platform) ? platform : null;
  const platformIntegrations =
    integrationPlatform === null
      ? []
      : integrations.filter((integration) => integration.provider === integrationPlatform);
  const integrationEmptyLabel =
    integrationPlatform === null ? '' : getIntegrationEmptyLabel(integrationPlatform);
  const agentLabel = integrationPlatform === null ? 'Agent' : getAgentLabel(integrationPlatform);
  const isEditing = environment !== null;
  const submitLabel = isEditing ? 'Save changes' : 'Add environment';
  const isSubmitDisabled = isPending || (evalGateEnabled && evalGateEvalConfigId === null);
  const environmentNameForPreview = name.trim() || 'production';
  const payloadPreview = useEnvironmentPayloadPreview({
    agentId,
    platform,
    environmentName: environmentNameForPreview,
    evalGateEnabled,
    evalGateEvalConfigId,
  });

  const handlePlatformChange = (value: AddEnvironmentFormValues['platform']) => {
    form.setValue('platform', value);
    if (isIntegrationPlatform(value)) {
      form.setValue('endpoint_url', null);

      if (platform !== value) {
        form.setValue('integration_id', null);
        form.setValue('platform_agent_id', null);
        form.setValue('platform_agent_name', null);
      }
      return;
    }
    form.setValue('integration_id', null);
    form.setValue('platform_agent_id', null);
    form.setValue('platform_agent_name', null);
  };

  const handleIntegrationChange = (id: string) => {
    form.setValue('integration_id', id || null);
    form.setValue('platform_agent_id', null);
    form.setValue('platform_agent_name', null);
  };

  const handleAgentChange = (id: string, name: string) => {
    form.setValue('platform_agent_id', id || null);
    form.setValue('platform_agent_name', name || null);
  };

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
    integrationId,
    platformIntegrations,
    integrationEmptyLabel,
    agentLabel,
    payloadOpen: payloadPreview.payloadOpen,
    onTogglePayloadOpen: payloadPreview.onTogglePayloadOpen,
    payloadPreview: payloadPreview.payloadPreview,
    isPayloadPreviewLoading: payloadPreview.isPayloadPreviewLoading,
    showMissingPublishedVersionInfo: payloadPreview.showMissingPublishedVersionInfo,
    submitLabel,
    isSubmitDisabled,
    handlePlatformChange,
    handleIntegrationChange,
    handleAgentChange,
    isPending,
    error,
  };
}
