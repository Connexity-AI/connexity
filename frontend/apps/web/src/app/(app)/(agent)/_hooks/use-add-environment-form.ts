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
  integration_id: '',
  platform_agent_id: '',
  platform_agent_name: '',
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

  const handleIntegrationChange = (id: string) => {
    form.setValue('integration_id', id);
    form.setValue('platform_agent_id', '');
    form.setValue('platform_agent_name', '');
  };

  const handleAgentChange = (id: string, name: string) => {
    form.setValue('platform_agent_id', id);
    form.setValue('platform_agent_name', name);
  };

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await mutateAsync({
        name: values.name,
        platform: values.platform,
        agent_id: agentId,
        integration_id: values.integration_id,
        platform_agent_id: values.platform_agent_id,
        platform_agent_name: values.platform_agent_name,
      });
      onSuccess();
    } catch {
      // Error surfaced via `error` and rendered by the form.
    }
  });

  return {
    form,
    onSubmit,
    integrationId,
    handleIntegrationChange,
    handleAgentChange,
    isPending,
    error,
  };
}
