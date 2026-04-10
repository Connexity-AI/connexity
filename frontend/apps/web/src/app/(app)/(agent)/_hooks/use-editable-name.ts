'use client';

import { useRef, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { updateAgent } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';

const editableNameSchema = z.object({
  name: z.string().min(1, 'Name is required'),
});

type EditableNameValues = z.infer<typeof editableNameSchema>;

export function useEditableName(agentId: string, agentName: string) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isEditing, setIsEditing] = useState(false);

  const form = useForm<EditableNameValues>({
    resolver: zodResolver(editableNameSchema),
    defaultValues: { name: agentName },
  });

  const { mutate: mutateAgentName } = useMutation({
    mutationFn: (name: string) => updateAgent(agentId, { name }),
    onMutate: async (newName) => {
      await queryClient.cancelQueries({ queryKey: agentKeys.detail(agentId) });
      const previous = queryClient.getQueryData(agentKeys.detail(agentId));
      queryClient.setQueryData(
        agentKeys.detail(agentId),
        (old: Record<string, unknown> | undefined) => (old ? { ...old, name: newName } : old)
      );
      return { previous };
    },
    onError: (_err, _name, context) => {
      if (context?.previous) {
        queryClient.setQueryData(agentKeys.detail(agentId), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists });
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) });
    },
  });

  const startEdit = () => {
    form.reset({ name: agentName });
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commit = () => {
    const trimmed = form.getValues('name').trim() || 'Untitled Agent';
    setIsEditing(false);
    if (trimmed !== agentName) {
      mutateAgentName(trimmed);
    }
  };

  const onSubmit = form.handleSubmit(() => {
    commit();
  });

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      form.reset({ name: agentName });
      setIsEditing(false);
    }
  };

  return {
    form,
    isEditing,
    inputRef,
    startEdit,
    commit,
    onSubmit,
    handleKeyDown,
  };
}
