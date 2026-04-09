'use client';

import { useState } from 'react';

import { useFieldArray, useFormContext } from 'react-hook-form';

import type {
  AgentFormValues,
  AgentToolValues,
} from '@/app/(app)/(agent)/_schemas/agent-form';

export function useToolsField() {
  const { control, watch } = useFormContext<AgentFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: 'tools' });

  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const tools = watch('tools');

  const openNew = () => {
    setIsCreating(true);
  };

  const openExisting = (index: number) => {
    setEditingIndex(index);
    setIsCreating(false);
  };

  const handleBack = () => {
    setEditingIndex(null);
    setIsCreating(false);
  };

  const handleDelete = () => {
    if (editingIndex === null) return;
    remove(editingIndex);
    handleBack();
  };

  const handleSaveNew = (tool: AgentToolValues) => {
    append(tool);
    setIsCreating(false);
  };

  return {
    fields,
    tools,
    editingIndex,
    isCreating,
    openNew,
    openExisting,
    handleBack,
    handleDelete,
    handleSaveNew,
  };
}
