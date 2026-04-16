'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { AgentsService } from '@/client/sdk.gen';
import { agentKeys } from '@/constants/query-keys';
import { getApiErrorMessage } from '@/utils/error';

import type { AgentGuidelinesPublic } from '@/client/types.gen';

const guidelinesSchema = z.object({
  guidelines: z.string().min(1, 'Guidelines cannot be empty'),
});

type GuidelinesFormValues = z.infer<typeof guidelinesSchema>;

interface UseAgentGuidelinesFormOptions {
  agentId: string;
  enabled: boolean;
  onSaved: () => void;
}

export function useAgentGuidelinesForm({
  agentId,
  enabled,
  onSaved,
}: UseAgentGuidelinesFormOptions) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: agentKeys.guidelines(agentId),

    queryFn: async (): Promise<AgentGuidelinesPublic> => {
      const result = await AgentsService.getAgentGuidelines({
        path: { agent_id: agentId },
      });
      if (result.error || !result.data) {
        throw new Error(
          `Failed to load guidelines: ${getApiErrorMessage(result.error)}`
        );
      }
      return result.data;
    },

    enabled,
    staleTime: Infinity,
  });

  const form = useForm<GuidelinesFormValues>({
    resolver: zodResolver(guidelinesSchema),
    defaultValues: { guidelines: '' },
    values: query.data ? { guidelines: query.data.guidelines } : undefined,
  });

  const saveMutation = useMutation({
    mutationFn: async (guidelines: string): Promise<AgentGuidelinesPublic> => {
      const result = await AgentsService.putAgentGuidelines({
        path: { agent_id: agentId },
        body: { guidelines },
      });
      if (result.error || !result.data) {
        throw new Error(
          `Failed to save guidelines: ${getApiErrorMessage(result.error)}`
        );
      }
      return result.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(agentKeys.guidelines(agentId), updated);
      onSaved();
    },
  });

  const resetMutation = useMutation({
    mutationFn: async (): Promise<AgentGuidelinesPublic> => {
      const result = await AgentsService.putAgentGuidelines({
        path: { agent_id: agentId },
        body: { guidelines: null },
      });
      if (result.error || !result.data) {
        throw new Error(
          `Failed to reset guidelines: ${getApiErrorMessage(result.error)}`
        );
      }
      return result.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(agentKeys.guidelines(agentId), updated);
      form.reset({ guidelines: updated.guidelines });
      onSaved();
    },
  });

  const onSubmit = form.handleSubmit(async ({ guidelines }) => {
    await saveMutation.mutateAsync(guidelines);
  });

  const resetToDefault = async (): Promise<void> => {
    await resetMutation.mutateAsync();
  };

  const queryError = query.error
    ? query.error instanceof Error
      ? query.error.message
      : 'Failed to load guidelines'
    : null;

  return {
    form,
    onSubmit,
    isLoading: query.isLoading,
    isSaving: saveMutation.isPending,
    isResetting: resetMutation.isPending,
    isDefault: query.data?.is_default ?? false,
    resetToDefault,
    queryError,
  };
}
