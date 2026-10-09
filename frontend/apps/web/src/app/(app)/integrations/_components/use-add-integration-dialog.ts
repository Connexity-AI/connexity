'use client';

import { useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { createIntegration } from '@/actions/integrations';
import { IntegrationProvider } from '@/client/types.gen';
import { integrationKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

import { getCreateIntegrationErrorMessage } from './add-integration-dialog.utils';

const formSchema = z
  .object({
    provider: z.enum([
      IntegrationProvider.RETELL,
      IntegrationProvider.VAPI,
      IntegrationProvider.ELEVENLABS,
      IntegrationProvider.N8N,
    ]),
    name: z.string().min(1, 'Name is required'),
    api_key: z.string().min(1, 'API key is required'),
    base_url: z.string(),
  })
  .refine((values) => values.provider !== IntegrationProvider.N8N || values.base_url.trim(), {
    path: ['base_url'],
    message: 'The address of your n8n instance is required',
  });

type FormValues = z.infer<typeof formSchema>;

export type DialogState = 'form' | 'testing' | 'success' | 'error';

export const PROVIDERS = [
  {
    value: IntegrationProvider.RETELL,
    label: 'Retell',
    placeholder: 'e.g., Production Retell',
    docsHref: 'https://dashboard.retellai.com/settings/api-keys',
    docsLabel: 'Get Retell API Key',
  },
  {
    value: IntegrationProvider.VAPI,
    label: 'Vapi',
    placeholder: 'e.g., Production Vapi',
    docsHref: 'https://dashboard.vapi.ai/org/api-keys',
    docsLabel: 'Get Vapi API Key',
  },
  {
    value: IntegrationProvider.ELEVENLABS,
    label: 'ElevenLabs',
    placeholder: 'e.g., Production ElevenLabs',
    docsHref: 'https://elevenlabs.io/app/settings/api-keys',
    docsLabel: 'Get ElevenLabs API Key',
  },
  {
    value: IntegrationProvider.N8N,
    label: 'n8n',
    placeholder: 'e.g., Production n8n',
    docsHref: 'https://docs.n8n.io/api/authentication/',
    docsLabel: 'Create an n8n API key',
  },
] as const;

const EMPTY_FORM: FormValues = {
  provider: IntegrationProvider.RETELL,
  name: '',
  api_key: '',
  base_url: '',
};

interface UseAddIntegrationDialogParams {
  onOpenChange: (open: boolean) => void;
}

export const useAddIntegrationDialog = ({
  onOpenChange,
}: UseAddIntegrationDialogParams) => {
  const queryClient = useQueryClient();

  const [dialogState, setDialogState] = useState<DialogState>('form');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: EMPTY_FORM,
    values: EMPTY_FORM,
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const needsAddress = values.provider === IntegrationProvider.N8N;
      const result = await createIntegration({
        provider: values.provider,
        name: values.name,
        api_key: values.api_key,
        base_url: needsAddress ? values.base_url.trim() : null,
      });

      if (isSuccessApiResult(result)) {
        return result.data;
      }

      const error = 'error' in result ? result.error : undefined;
      throw new Error(getCreateIntegrationErrorMessage(error));
    },
    onMutate: () => {
      setDialogState('testing');
      setErrorMessage('');
    },
    onSuccess: () => {
      setDialogState('success');
      void queryClient.invalidateQueries({ queryKey: integrationKeys.all });
      setTimeout(() => onOpenChange(false), 1500);
    },
    onError: (error: Error) => {
      setErrorMessage(error.message);
      setDialogState('error');
    },
  });

  const provider = form.watch('provider');
  const selectedProvider = PROVIDERS.find((item) => item.value === provider) ?? PROVIDERS[0];

  const handleOpenChange = (next: boolean) => {
    if (dialogState === 'testing' && !next) {
      return;
    }

    onOpenChange(next);
  };

  const onSubmit = form.handleSubmit((values) => mutation.mutate(values));

  return {
    form,
    needsAddress: provider === IntegrationProvider.N8N,
    dialogState,
    errorMessage,
    selectedProvider,
    handleOpenChange,
    onSubmit,
  };
};
