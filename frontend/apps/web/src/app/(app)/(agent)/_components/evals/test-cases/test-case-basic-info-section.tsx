'use client';
'use no memo';

import { useState } from 'react';

import { Plus, X } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import {
  FieldLabel,
  SectionLabel,
} from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';

function TagChip({ tag, onRemove }: { tag: string; onRemove: (tag: string) => void }) {
  return (
    <span className="flex items-center gap-1 rounded bg-accent px-2 py-0.5 text-xs text-muted-foreground">
      {tag}
      <button
        type="button"
        onClick={() => onRemove(tag)}
        className="text-muted-foreground/50 transition-colors hover:text-red-400"
      >
        <X className="h-2.5 w-2.5" />
      </button>
    </span>
  );
}

function TagsField() {
  const form = useFormContext<TestCaseFormValues>();
  const tags = form.watch('tags');
  const [tagInput, setTagInput] = useState('');

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (!trimmed || tags.includes(trimmed)) return;
    form.setValue('tags', [...tags, trimmed], { shouldDirty: true });
    setTagInput('');
  };

  const handleRemoveTag = (tag: string) => {
    form.setValue(
      'tags',
      tags.filter((existing) => existing !== tag),
      { shouldDirty: true }
    );
  };

  return (
    <div>
      <FieldLabel>Tags</FieldLabel>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <TagChip key={tag} tag={tag} onRemove={handleRemoveTag} />
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={tagInput}
          onChange={(event) => setTagInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              handleAddTag();
            }
          }}
          placeholder="Add tag..."
          className="h-7 flex-1 text-xs"
        />

        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleAddTag}
          disabled={!tagInput.trim()}
          className="h-7 px-2 text-xs"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

export function TestCaseBasicInfoSection() {
  const form = useFormContext<TestCaseFormValues>();

  return (
    <div>
      <SectionLabel>Basic Info</SectionLabel>
      <div className="space-y-3">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FieldLabel>Name</FieldLabel>
              <FormControl>
                <Input {...field} className="h-8 text-sm" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="difficulty"
            render={({ field }) => (
              <FormItem>
                <FieldLabel>Difficulty</FieldLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="h-8 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
                <FieldLabel>Status</FieldLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="h-8 text-sm">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="archived">Archived</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <TagsField />
      </div>
    </div>
  );
}
