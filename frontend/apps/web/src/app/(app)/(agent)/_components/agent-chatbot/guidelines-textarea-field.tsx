'use client';

import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@workspace/ui/components/ui/form';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import type { Control } from 'react-hook-form';

interface GuidelinesTextareaFieldProps {
  control: Control<{ guidelines: string }>;
  isLoading: boolean;
  queryError: string | null;
}

export function GuidelinesTextareaField({
  control,
  isLoading,
  queryError,
}: GuidelinesTextareaFieldProps) {
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading guidelines…</p>;
  }

  if (queryError) {
    return <p className="text-sm text-destructive">{queryError}</p>;
  }

  return (
    <FormField
      control={control}
      name="guidelines"
      render={({ field }) => (
        <FormItem className="flex-1 flex flex-col min-h-0">
          <FormControl>
            <Textarea
              {...field}
              placeholder="Write guidelines for the assistant…"
              className="flex-1 resize-none font-mono text-xs min-h-0"
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
