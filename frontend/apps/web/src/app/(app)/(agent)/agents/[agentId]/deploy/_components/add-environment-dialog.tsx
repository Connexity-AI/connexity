'use client';

import { useEffect } from 'react';
import Link from 'next/link';

import { zodResolver } from '@hookform/resolvers/zod';
import { AlertTriangle, Check, Loader2 } from 'lucide-react';
import { useForm } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
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

import { useCreateEnvironment } from '@/app/(app)/(agent)/_hooks/use-create-environment';
import { useRetellAgents } from '@/app/(app)/(agent)/_hooks/use-retell-agents';
import { addEnvironmentFormSchema } from './add-environment-form-schema';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';
import type { AddEnvironmentFormValues } from './add-environment-form-schema';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
  integrations: IntegrationPublic[];
}

function AgentSelectField({
  integrationId,
  value,
  onChange,
  onNameChange,
  disabled,
}: {
  integrationId: string | null;
  value: string;
  onChange: (id: string) => void;
  onNameChange: (name: string) => void;
  disabled: boolean;
}) {
  const { data: rawAgents, isLoading } = useRetellAgents(integrationId);
  const agents = rawAgents
    ? Object.values(
        rawAgents.reduce<Record<string, (typeof rawAgents)[number]>>((acc, agent) => {
          const prev = acc[agent.agent_id];
          if (!prev) {
            acc[agent.agent_id] = agent;
            return acc;
          }
          const prevPublished = prev.is_published ?? false;
          const currPublished = agent.is_published ?? false;
          if (currPublished && !prevPublished) {
            acc[agent.agent_id] = agent;
          } else if (currPublished === prevPublished) {
            if ((agent.version ?? -Infinity) > (prev.version ?? -Infinity)) {
              acc[agent.agent_id] = agent;
            }
          }
          return acc;
        }, {})
      )
    : undefined;

  const placeholder = isLoading
    ? 'Loading agents…'
    : !integrationId
      ? 'Select integration first…'
      : 'Select a Retell agent…';

  return (
    <Select
      value={value}
      onValueChange={(id) => {
        const selected = agents?.find((a) => a.agent_id === id);
        onChange(id);
        onNameChange(selected?.agent_name ?? id);
      }}
      disabled={disabled || !integrationId || isLoading}
    >
      <SelectTrigger className="h-9 text-xs">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {agents?.map((agent) => (
          <SelectItem key={agent.agent_id} value={agent.agent_id} className="text-xs">
            {agent.agent_name ?? agent.agent_id}
          </SelectItem>
        ))}
        {!isLoading && integrationId && agents?.length === 0 && (
          <div className="px-3 py-2 text-xs text-muted-foreground">No agents found</div>
        )}
      </SelectContent>
    </Select>
  );
}

export const AddEnvironmentDialog: FC<Props> = ({ open, onOpenChange, agentId, integrations }) => {
  const retellIntegrations = integrations.filter((i) => i.provider === 'retell');
  const hasIntegrations = retellIntegrations.length > 0;

  const { mutateAsync, isPending, error } = useCreateEnvironment(agentId);

  const form = useForm<AddEnvironmentFormValues>({
    resolver: zodResolver(addEnvironmentFormSchema),
    defaultValues: {
      name: '',
      platform: 'retell',
      integration_id: '',
      platform_agent_id: '',
      platform_agent_name: '',
    },
  });

  const watchedIntegrationId = form.watch('integration_id');

  useEffect(() => {
    if (open) {
      form.reset({
        name: '',
        platform: 'retell',
        integration_id: '',
        platform_agent_id: '',
        platform_agent_name: '',
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleIntegrationChange = (integrationId: string) => {
    form.setValue('integration_id', integrationId);
    form.setValue('platform_agent_id', '');
    form.setValue('platform_agent_name', '');
  };

  const onSubmit = async (values: AddEnvironmentFormValues) => {
    try {
      await mutateAsync({
        name: values.name,
        platform: values.platform,
        agent_id: agentId,
        integration_id: values.integration_id,
        platform_agent_id: values.platform_agent_id,
        platform_agent_name: values.platform_agent_name,
      });
      onOpenChange(false);
    } catch {
      // Error is exposed via `error` from useCreateEnvironment and rendered below.
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !isPending && onOpenChange(o)}>
      <DialogContent className="sm:max-w-lg max-w-lg flex flex-col max-h-[90vh] p-6 gap-4">
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-lg leading-none font-semibold">Add environment</DialogTitle>
        </DialogHeader>

        {!hasIntegrations ? (
          <div className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
              <AlertTriangle className="w-4 h-4 shrink-0 text-yellow-500 mt-0.5" />
              <p className="text-sm text-yellow-600 dark:text-yellow-400">
                No Retell integrations found. Add one before creating an environment.
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button asChild size="sm">
                <Link href="/integrations">Go to Integrations</Link>
              </Button>
            </div>
          </div>
        ) : (
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="flex flex-col flex-1 min-h-0 gap-0"
            >
              <div className="overflow-y-auto flex-1 min-h-0 px-1">
                <div className="space-y-5 pt-1 pb-1">
                  {/* Name */}
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

                  {/* Platform */}
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

                  {/* Integration */}
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
                            {retellIntegrations.map((i) => (
                              <SelectItem
                                key={i.id}
                                value={i.id}
                                className="text-xs pl-3 pr-3 [&>span:first-child]:hidden"
                              >
                                <span className="flex w-full items-center justify-between gap-2">
                                  {i.name}
                                  {field.value === i.id && (
                                    <Check className="h-3.5 w-3.5 shrink-0" />
                                  )}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Agent */}
                  <FormField
                    control={form.control}
                    name="platform_agent_id"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel>Agent</FormLabel>
                        <FormControl>
                          <AgentSelectField
                            integrationId={watchedIntegrationId || null}
                            value={field.value}
                            onChange={(id) => form.setValue('platform_agent_id', id)}
                            onNameChange={(name) => form.setValue('platform_agent_name', name)}
                            disabled={isPending}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {error && (
                <p className="text-sm text-destructive px-1 pt-1 shrink-0">{error}</p>
              )}
              <div className="flex justify-end gap-2 pt-1 shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenChange(false)}
                  disabled={isPending}
                >
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
        )}
      </DialogContent>
    </Dialog>
  );
};
