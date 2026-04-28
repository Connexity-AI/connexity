'use client';

import { useFormContext } from 'react-hook-form';

import { TabsContent } from '@workspace/ui/components/ui/tabs';
import { Slider } from '@workspace/ui/components/ui/slider';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@workspace/ui/components/ui/form';

import { LlmModelPicker } from '@/app/(app)/(agent)/_components/llm/llm-model-picker';
import { temperatureLabel } from '@/app/(app)/(agent)/_constants/agent';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { SettingsTabSkeleton } from '@/app/(app)/(agent)/_components/settings/settings-tab-skeleton';

export function SettingsTab() {
  const form = useFormContext<AgentFormValues>();
  const { isReadOnly, isLoading } = useAgentEditFormActions();
  const provider = form.watch('provider');
  const temperature = form.watch('temperature');

  if (isLoading) return <SettingsTabSkeleton />;

  return (
    <TabsContent value="settings" className="flex-1 mt-0 overflow-auto">
      <div className="px-6 pt-6 pb-2 max-w-xl">
        <p className="text-xs text-muted-foreground uppercase tracking-wider pb-3 border-b border-border">
          Model
        </p>
      </div>
      <div className="px-6 pb-6 max-w-xl space-y-8">
        <FormField
          control={form.control}
          name="model"
          render={({ field }) => (
            <FormItem className="space-y-2">
              <FormLabel className="text-sm text-foreground">Model</FormLabel>
              <LlmModelPicker
                value={field.value}
                provider={provider}
                onSelect={(modelOption) => {
                  form.setValue('provider', modelOption.provider, { shouldDirty: true });
                  field.onChange(modelOption.model);
                }}
                disabled={isReadOnly}
              />
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Temperature */}
        <FormField
          control={form.control}
          name="temperature"
          render={({ field }) => (
            <FormItem className="space-y-3">
              <div className="flex items-center justify-between">
                <FormLabel className="text-sm text-foreground">Temperature</FormLabel>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {temperatureLabel(temperature)}
                  </span>
                  <span className="text-sm font-mono text-foreground tabular-nums w-8 text-right">
                    {temperature.toFixed(1)}
                  </span>
                </div>
              </div>
              <FormControl>
                <Slider
                  min={0}
                  max={2}
                  step={0.1}
                  value={[field.value]}
                  onValueChange={(value) => field.onChange(value[0] ?? 0.7)}
                  disabled={isReadOnly}
                />
              </FormControl>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0.0</span>
                <span>1.0</span>
                <span>2.0</span>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
    </TabsContent>
  );
}
