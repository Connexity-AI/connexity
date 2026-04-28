'use client';

import { Check, Loader2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { useAddEnvironmentForm } from '@/app/(app)/(agent)/_hooks/use-add-environment-form';
import { AgentSelectField } from './agent-select-field';

import type { FC } from 'react';
import type { IntegrationPublic } from '@/client/types.gen';

interface Props {
  agentId: string;
  integrations: IntegrationPublic[];
  onCancel: () => void;
  onSuccess: () => void;
}

export const AddEnvironmentForm: FC<Props> = ({ agentId, integrations, onCancel, onSuccess }) => {
  const { form, onSubmit, integrationId, handleIntegrationChange, handleAgentChange, isPending, error } =
    useAddEnvironmentForm({ agentId, onSuccess });

  return (
    <Form {...form}>
      <form onSubmit={onSubmit} className="flex flex-col flex-1 min-h-0 gap-0">
        <div className="overflow-y-auto flex-1 min-h-0 px-1">
          <div className="space-y-5 pt-1 pb-1">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem className="space-y-1.5">
                  <FormLabel htmlFor="env-name">Name</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      id="env-name"
                      placeholder="e.g. Production, Staging, Dev"
                      disabled={isPending}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-1.5">
              <FormLabel>Platform</FormLabel>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  className="flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all border-foreground/40 bg-accent"
                >
                  <span className="text-xs text-foreground">Retell</span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    Push directly via Retell API (requires integration)
                  </span>
                </button>
              </div>
            </div>

            <FormField
              control={form.control}
              name="integration_id"
              render={({ field }) => (
                <FormItem className="space-y-1.5">
                  <FormLabel>Integration</FormLabel>
                  <Select
                    value={field.value || undefined}
                    onValueChange={handleIntegrationChange}
                    disabled={isPending}
                  >
                    <FormControl>
                      <SelectTrigger className="h-9 text-xs">
                        <SelectValue placeholder="Select an integration…" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {integrations.map((i) => (
                        <SelectItem
                          key={i.id}
                          value={i.id}
                          className="text-xs pl-3 pr-3 [&>span:first-child]:hidden"
                        >
                          <span className="flex w-full items-center justify-between gap-2">
                            {i.name}
                            {field.value === i.id && <Check className="h-3.5 w-3.5 shrink-0" />}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="platform_agent_id"
              render={({ field }) => (
                <FormItem className="space-y-1.5">
                  <FormLabel>Agent</FormLabel>
                  <FormControl>
                    <AgentSelectField
                      integrationId={integrationId || null}
                      value={field.value}
                      onChange={handleAgentChange}
                      disabled={isPending}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        {error && <p className="text-sm text-destructive px-1 pt-1 shrink-0">{error}</p>}

        <div className="flex justify-end gap-2 pt-1 shrink-0">
          <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Saving…
              </>
            ) : (
              'Add environment'
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
};
