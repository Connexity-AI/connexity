'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { useCreateEnvironment } from '@/app/(app)/(agent)/_hooks/use-create-environment';
import { useUpdateEnvironment } from '@/app/(app)/(agent)/_hooks/use-update-environment';
import { addEnvironmentFormSchema } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import {
  getEnvironmentCreateBody,
  getEnvironmentFormValues,
  getEnvironmentUpdateBody,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/environment-form-values';

import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
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
  const createEnvironment = useCreateEnvironment(agentId);
  const updateEnvironment = useUpdateEnvironment(agentId);

  const form = useForm<AddEnvironmentFormValues>({
    resolver: zodResolver(addEnvironmentFormSchema),
    defaultValues: getEnvironmentFormValues(environment),
    values: getEnvironmentFormValues(environment),
  });

  const integrationId = form.watch('integration_id');
  const platform = form.watch('platform');
  const isPending = createEnvironment.isPending || updateEnvironment.isPending;
  const error = createEnvironment.error ?? updateEnvironment.error;

  const handlePlatformChange = (value: AddEnvironmentFormValues['platform']) => {
    form.setValue('platform', value);
    if (value === 'retell' || value === 'vapi') {
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
    integrationId,
    handlePlatformChange,
    handleIntegrationChange,
    handleAgentChange,
    isPending,
    error,
  };
}
