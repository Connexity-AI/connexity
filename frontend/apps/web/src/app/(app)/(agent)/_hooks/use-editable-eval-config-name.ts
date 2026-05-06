'use client';

import { useRef, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { updateEvalConfig } from '@/actions/eval-configs';
import { evalConfigKeys } from '@/constants/query-keys';

const editableNameSchema = z.object({
  name: z.string().min(1, 'Name is required'),
});

type EditableNameValues = z.infer<typeof editableNameSchema>;

interface UseEditableEvalConfigNameOptions {
  evalConfigId: string;
  agentId: string;
  name: string;
  onRenamed?: (name: string) => void;
}

export function useEditableEvalConfigName({
  evalConfigId,
  agentId,
  name,
  onRenamed,
}: UseEditableEvalConfigNameOptions) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isEditing, setIsEditing] = useState(false);

  const form = useForm<EditableNameValues>({
    resolver: zodResolver(editableNameSchema),
    defaultValues: { name },
  });

  const { mutate: mutateConfigName } = useMutation({
    mutationFn: (newName: string) => updateEvalConfig(evalConfigId, { name: newName }),
    onMutate: async (newName) => {
      await queryClient.cancelQueries({ queryKey: evalConfigKeys.detail(evalConfigId) });
      const previous = queryClient.getQueryData(evalConfigKeys.detail(evalConfigId));
      queryClient.setQueryData(
        evalConfigKeys.detail(evalConfigId),
        (old: Record<string, unknown> | undefined) => (old ? { ...old, name: newName } : old)
      );
      onRenamed?.(newName);
      return { previous };
    },
    onError: (_err, _name, context) => {
      if (context?.previous) {
        queryClient.setQueryData(evalConfigKeys.detail(evalConfigId), context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: evalConfigKeys.detail(evalConfigId) });
      queryClient.invalidateQueries({ queryKey: evalConfigKeys.list(agentId) });
    },
  });

  const startEdit = () => {
    form.reset({ name });
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commit = () => {
    const trimmed = form.getValues('name').trim() || 'Untitled Eval Config';
    setIsEditing(false);
    if (trimmed !== name) {
      mutateConfigName(trimmed);
    }
  };

  const onSubmit = form.handleSubmit(() => {
    commit();
  });

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      form.reset({ name });
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
