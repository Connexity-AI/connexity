'use client';

import { useFormContext } from 'react-hook-form';

import { TabsContent } from '@workspace/ui/components/ui/tabs';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import {
  FormField,
  FormItem,
  FormControl,
  FormMessage,
} from '@workspace/ui/components/ui/form';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';

export function PromptTab() {
  const form = useFormContext<AgentFormValues>();
  const { isReadOnly } = useAgentEditFormActions();

  return (
    <TabsContent value="prompt" className="flex-1 mt-0 p-6 flex flex-col min-h-0">
      <FormField
        control={form.control}
        name="prompt"
        render={({ field }) => (
          <FormItem className="flex-1 flex flex-col min-h-0">
            <FormControl>
              <Textarea
                {...field}
                placeholder="Enter your prompt here..."
                className="w-full flex-1 resize-none min-h-0"
                readOnly={isReadOnly}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </TabsContent>
  );
}
