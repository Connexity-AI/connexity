'use client';
'use no memo';

import { useFormContext } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import {
  FieldLabel,
  SectionLabel,
} from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';

export function TestCaseUserSimulationSection() {
  const form = useFormContext<TestCaseFormValues>();

  return (
    <div>
      <SectionLabel>User Simulation</SectionLabel>
      <div className="space-y-3">
        <FormField
          control={form.control}
          name="first_turn"
          render={({ field }) => (
            <FormItem>
              <FieldLabel>First Speaker</FieldLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="agent">Agent</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="first_message"
          render={({ field }) => (
            <FormItem>
              <FieldLabel>Initial Message</FieldLabel>
              <FormControl>
                <Textarea
                  {...field}
                  placeholder="The first message to start the conversation..."
                  className="min-h-15 resize-none text-sm leading-relaxed"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="persona_context"
          render={({ field }) => (
            <FormItem>
              <FieldLabel>Persona Context</FieldLabel>
              <FormControl>
                <Textarea
                  {...field}
                  placeholder="Describe the persona (type, description, behavioral instructions)..."
                  className="h-64 resize-none font-mono text-sm leading-relaxed"
                />
              </FormControl>
              <p className="mt-1.5 text-[10px] leading-relaxed text-muted-foreground/40">
                Use section headers: <span className="font-mono">[Persona type]</span> ·{' '}
                <span className="font-mono">[Description]</span> ·{' '}
                <span className="font-mono">[Behavioral instructions]</span>
              </p>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
    </div>
  );
}
