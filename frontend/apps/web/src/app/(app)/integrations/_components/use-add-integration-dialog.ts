'use client';

import { useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { createIntegration } from '@/actions/integrations';
import { integrationKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

import { getCreateIntegrationErrorMessage } from './add-integration-dialog.utils';

const formSchema = z.object({
  provider: z.enum(['retell', 'vapi']),
  name: z.string().min(1, 'Name is required'),
  api_key: z.string().min(1, 'API key is required'),
});

type FormValues = z.infer<typeof formSchema>;

export type DialogState = 'form' | 'testing' | 'success' | 'error';

export const PROVIDERS = [
  {
    value: 'retell',
    label: 'Retell',
    placeholder: 'e.g., Production Retell',
    docsHref: 'https://dashboard.retellai.com/settings/api-keys',
    docsLabel: 'Get Retell API Key',
  },
  {
    value: 'vapi',
    label: 'Vapi',
    placeholder: 'e.g., Production Vapi',
    docsHref: 'https://dashboard.vapi.ai/org/api-keys',
    docsLabel: 'Get Vapi API Key',
  },
] as const;

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
    defaultValues: { provider: 'retell', name: '', api_key: '' },
    values: { provider: 'retell', name: '', api_key: '' },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const result = await createIntegration(values);

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
    dialogState,
    errorMessage,
    selectedProvider,
    handleOpenChange,
    onSubmit,
  };
};
