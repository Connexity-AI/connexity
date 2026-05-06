'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { useCreateEnvironment } from '@/app/(app)/(agent)/_hooks/use-create-environment';
import {
  addEnvironmentFormSchema,
  type AddEnvironmentFormValues,
} from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';

const DEFAULT_VALUES: AddEnvironmentFormValues = {
  name: '',
  platform: 'retell',
  integration_id: null,
  platform_agent_id: null,
  platform_agent_name: null,
  endpoint_url: null,
  eval_gate_enabled: false,
  eval_gate_eval_config_id: null,
};

interface UseAddEnvironmentFormOptions {
  agentId: string;
  onSuccess: () => void;
}

export function useAddEnvironmentForm({ agentId, onSuccess }: UseAddEnvironmentFormOptions) {
  const { mutateAsync, isPending, error } = useCreateEnvironment(agentId);

  const form = useForm<AddEnvironmentFormValues>({
    resolver: zodResolver(addEnvironmentFormSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const integrationId = form.watch('integration_id');
  const platform = form.watch('platform');

  const handlePlatformChange = (value: AddEnvironmentFormValues['platform']) => {
    form.setValue('platform', value);
    if (value === 'retell') {
      form.setValue('endpoint_url', null);
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
      await mutateAsync({
        name: values.name,
        platform: values.platform,
        agent_id: agentId,
        integration_id: values.integration_id,
        platform_agent_id: values.platform_agent_id,
        platform_agent_name:
          values.platform === 'retell'
            ? (values.platform_agent_name ?? values.platform_agent_id)
            : values.platform_agent_name,
        endpoint_url: values.endpoint_url,
        eval_gate_eval_config_id: values.eval_gate_enabled
          ? values.eval_gate_eval_config_id
          : null,
      });
      onSuccess();
    } catch {
      // Error surfaced via `error` and rendered by the form.
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
