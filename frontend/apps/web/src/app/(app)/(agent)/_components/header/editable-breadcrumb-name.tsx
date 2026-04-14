'use client';

import { Pencil } from 'lucide-react';

import { BreadcrumbItem } from '@workspace/ui/components/ui/breadcrumb';
import { Button } from '@workspace/ui/components/ui/button';
import { Form, FormControl, FormField, FormItem } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';

import { useEditableName } from '@/app/(app)/(agent)/_hooks/use-editable-name';

interface EditableBreadcrumbNameProps {
  agentId: string;
  agentName: string;
}

export function EditableBreadcrumbName({ agentId, agentName }: EditableBreadcrumbNameProps) {
  const { form, isEditing, inputRef, startEdit, commit, onSubmit, handleKeyDown } = useEditableName(
    agentId,
    agentName
  );

  if (isEditing) {
    return (
      <BreadcrumbItem>
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
                      className="h-7 w-44 px-2 text-sm"
                      autoFocus
                    />
                  </FormControl>
                </FormItem>
              )}
            />
          </form>
        </Form>
      </BreadcrumbItem>
    );
  }

  return (
    <BreadcrumbItem>
      <Button
        variant="ghost"
        size="sm"
        onClick={startEdit}
        title="Click to rename"
        className="group gap-1.5 max-w-44 px-1.5 h-7"
      >
        <span className="truncate">{agentName}</span>
        <Pencil className="w-3 h-3 text-muted-foreground/0 group-hover:text-muted-foreground/60 transition-colors shrink-0" />
      </Button>
    </BreadcrumbItem>
  );
}
