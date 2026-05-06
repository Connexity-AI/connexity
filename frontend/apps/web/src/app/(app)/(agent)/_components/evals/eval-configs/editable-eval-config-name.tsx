'use client';

import { Pencil } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Form, FormControl, FormField, FormItem } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';

import { useEditableEvalConfigName } from '@/app/(app)/(agent)/_hooks/use-editable-eval-config-name';

interface EditableEvalConfigNameProps {
  evalConfigId: string;
  agentId: string;
  name: string;
  onRenamed?: (name: string) => void;
}

export function EditableEvalConfigName({
  evalConfigId,
  agentId,
  name,
  onRenamed,
}: EditableEvalConfigNameProps) {
  const { form, isEditing, inputRef, startEdit, commit, onSubmit, handleKeyDown } =
    useEditableEvalConfigName({ evalConfigId, agentId, name, onRenamed });

  if (isEditing) {
    return (
      <Form {...form}>
        <form onSubmit={onSubmit}>
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Input
                    {...field}
                    ref={inputRef}
                    onBlur={commit}
                    onKeyDown={handleKeyDown}
                    className="h-7 w-64 px-2 text-sm"
                    autoFocus
                  />
                </FormControl>
              </FormItem>
            )}
          />
        </form>
      </Form>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={startEdit}
      title="Click to rename"
      className="group h-7 max-w-64 gap-1.5 px-1.5"
    >
      <span className="truncate">{name}</span>
      <Pencil className="h-3 w-3 shrink-0 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60" />
    </Button>
  );
}
