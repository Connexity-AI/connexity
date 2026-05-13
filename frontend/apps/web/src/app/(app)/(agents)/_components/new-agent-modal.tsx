'use client';

import { useEffect, useMemo } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, AudioLines, Bot, FileText, Layers, Phone, Sparkles } from 'lucide-react';
import { useForm } from 'react-hook-form';

import { integrationsListQuery } from '@/app/(app)/(agent)/_queries/integrations-list-query';
import { useCreateDraftAgent } from '@/app/(app)/(agents)/_hooks/use-create-draft-agent';
import {
  newAgentFormSchema,
  type NewAgentFormValues,
} from '@/app/(app)/(agents)/_components/new-agent-form-schema';
import { platformLabel } from '@/app/(app)/(agents)/_components/new-agent-platform-labels';
import {
  listElevenlabsAgents,
  listRetellAgents,
  listVapiAssistants,
} from '@/actions/integrations';
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
import { cn } from '@workspace/ui/lib/utils';
import { IntegrationProviderInput, Platform } from '@/client/types.gen';
import { isSuccessApiResult } from '@/utils/api';

import type { FC } from 'react';
import type { CreateAgentDraftPayload } from '@/actions/agents';
import type { IntegrationPublic, RetellAgentSummary } from '@/client/types.gen';

const PLATFORM_OPTIONS: {
  value: Platform;
  label: string;
  description: string;
  icon: typeof Bot;
}[] = [
  { value: Platform.WEBHOOK, label: 'Custom', description: 'Webhook or bring your own stack', icon: Bot },
  { value: Platform.RETELL, label: 'Retell', description: 'Retell AI voice agents', icon: Phone },
  { value: Platform.VAPI, label: 'Vapi', description: 'Vapi voice agents', icon: Sparkles },
  {
    value: Platform.ELEVENLABS,
    label: 'ElevenLabs',
    description: 'ElevenLabs conversational AI',
    icon: AudioLines,
  },
];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const defaultValues: NewAgentFormValues = {
  name: '',
  platform: null,
  integration_id: null,
  platform_agent_id: null,
  platform_agent_name: null,
};

function integrationProviderForPlatform(platform: Platform): IntegrationProviderInput {
  if (platform === Platform.RETELL) {
    return IntegrationProviderInput.RETELL;
  }
  if (platform === Platform.VAPI) {
    return IntegrationProviderInput.VAPI;
  }
  return IntegrationProviderInput.ELEVENLABS;
}

export const NewAgentModal: FC<Props> = ({ open, onOpenChange }) => {
  const { mutateAsync, isPending, error } = useCreateDraftAgent();
  const integrationsQuery = useQuery(integrationsListQuery());

  const form = useForm<NewAgentFormValues>({
    resolver: zodResolver(newAgentFormSchema),
    defaultValues,
  });

  const platform = form.watch('platform');
  const integrationId = form.watch('integration_id');

  useEffect(() => {
    if (!open) {
      form.reset(defaultValues);
    }
  }, [open, form]);

  const availableIntegrations = useMemo(() => {
    const integrations: IntegrationPublic[] = integrationsQuery.data?.data ?? [];
    if (platform === null || platform === Platform.WEBHOOK) return [];
    const want = integrationProviderForPlatform(platform);
    return integrations.filter((i) => i.provider === want);
  }, [integrationsQuery.data, platform]);

  const catalogQuery = useQuery({
    queryKey: ['new-agent-catalog', platform, integrationId],
    enabled:
      open &&
      platform !== null &&
      platform !== Platform.WEBHOOK &&
      Boolean(integrationId) &&
      (integrationId?.length ?? 0) > 0,
    queryFn: async (): Promise<RetellAgentSummary[]> => {
      if (!integrationId || platform === null || platform === Platform.WEBHOOK) return [];
      if (platform === Platform.RETELL) {
        const r = await listRetellAgents(integrationId);
        if (!isSuccessApiResult(r)) throw new Error('Failed to load Retell agents');
        return r.data;
      }
      if (platform === Platform.VAPI) {
        const r = await listVapiAssistants(integrationId);
        if (!isSuccessApiResult(r)) throw new Error('Failed to load Vapi assistants');
        return r.data;
      }
      const r = await listElevenlabsAgents(integrationId);
      if (!isSuccessApiResult(r)) throw new Error('Failed to load ElevenLabs agents');
      return r.data;
    },
  });

  const catalog = catalogQuery.data ?? [];

  const onSubmit = async (values: NewAgentFormValues) => {
    if (values.platform === null) {
      return;
    }
    const payload: CreateAgentDraftPayload = {
      name: values.name.trim(),
      platform: values.platform,
      prompt_type: 'single_prompt',
      integration_id: values.platform === Platform.WEBHOOK ? null : values.integration_id,
      platform_agent_id:
        values.platform === Platform.WEBHOOK ? null : values.platform_agent_id,
      platform_agent_name:
        values.platform === Platform.WEBHOOK ? null : values.platform_agent_name,
    };
    await mutateAsync(payload);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg flex flex-col max-h-[90vh]">
        <DialogHeader className="shrink-0">
          <DialogTitle>New agent</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col flex-1 min-h-0 gap-0"
          >
            <div className="overflow-y-auto flex-1 min-h-0 pr-1">
              <div className="space-y-5 pt-1 pb-1">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5 px-1">
                      <FormLabel htmlFor="new-agent-name">Agent name</FormLabel>
                      <FormControl>
                        <Input
                          id="new-agent-name"
                          placeholder="e.g. Kate (Plumbing Co.)"
                          className="h-9 text-xs"
                          disabled={isPending}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="platform"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel>Platform</FormLabel>
                      <div className="grid grid-cols-2 gap-2">
                        {PLATFORM_OPTIONS.map((p) => {
                          const active = field.value === p.value;
                          const Icon = p.icon;
                          return (
                            <button
                              key={p.value}
                              type="button"
                              disabled={isPending}
                              onClick={() => {
                                field.onChange(p.value);
                                form.setValue('integration_id', null);
                                form.setValue('platform_agent_id', null);
                                form.setValue('platform_agent_name', null);
                              }}
                              className={cn(
                                'flex items-start gap-2.5 px-3 py-2.5 rounded-lg border text-left transition-all',
                                active
                                  ? 'border-foreground/40 bg-accent'
                                  : 'border-border bg-transparent hover:bg-accent/40'
                              )}
                            >
                              <Icon
                                className={cn(
                                  'w-4 h-4 mt-0.5 shrink-0',
                                  active ? 'text-foreground' : 'text-muted-foreground'
                                )}
                              />
                              <div className="min-w-0 flex-1">
                                <p className="text-xs text-foreground">{p.label}</p>
                                <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">
                                  {p.description}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {platform !== null && (
                  <div className="space-y-1.5">
                    <p className="text-sm font-medium leading-none">Prompt mode</p>
                  <div className="grid grid-cols-1 gap-2">
                    <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-foreground/40 bg-accent text-left">
                      <FileText className="w-4 h-4 mt-0.5 shrink-0 text-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-foreground">Single prompt</p>
                        <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">
                          One system prompt with versioning and deployments
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-border opacity-50 cursor-not-allowed text-left">
                      <Layers className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <p className="text-xs text-foreground">Multi prompt</p>
                          <span className="text-[9px] uppercase tracking-wider px-1 py-0.5 rounded bg-accent text-muted-foreground">
                            Coming soon
                          </span>
                        </div>
                        <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">
                          Multiple prompts — observe and evaluate only
                        </p>
                      </div>
                    </div>
                  </div>
                  </div>
                )}

                {platform !== null && platform !== Platform.WEBHOOK && (
                  <>
                    <FormField
                      control={form.control}
                      name="integration_id"
                      render={({ field }) => (
                        <FormItem className="space-y-1.5 px-1">
                          <FormLabel>Integration</FormLabel>
                          {availableIntegrations.length === 0 ? (
                            <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border text-[11px] text-muted-foreground">
                              <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
                              No {platformLabel(platform)} integrations found. Add one under
                              Integrations first.
                            </div>
                          ) : (
                            <Select
                              value={field.value ?? undefined}
                              onValueChange={(v) => {
                                field.onChange(v);
                                form.setValue('platform_agent_id', null);
                                form.setValue('platform_agent_name', null);
                              }}
                              disabled={isPending}
                            >
                              <FormControl>
                                <SelectTrigger className="h-9 text-xs">
                                  <SelectValue placeholder="Select an integration…" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {availableIntegrations.map((i) => (
                                  <SelectItem key={i.id} value={i.id} className="text-xs">
                                    {i.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {integrationId && (
                      <FormField
                        control={form.control}
                        name="platform_agent_id"
                        render={({ field }) => {
                          let agentSelect: React.ReactNode;
                          if (catalogQuery.isLoading) {
                            agentSelect = (
                              <p className="text-[11px] text-muted-foreground">Loading agents…</p>
                            );
                          } else if (catalog.length === 0) {
                            agentSelect = (
                              <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border text-[11px] text-muted-foreground">
                                <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
                                No agents found in this integration.
                              </div>
                            );
                          } else {
                            agentSelect = (
                              <Select
                                value={field.value ?? undefined}
                                onValueChange={(id) => {
                                  const row = catalog.find((a) => a.agent_id === id);
                                  field.onChange(id);
                                  form.setValue('platform_agent_name', row?.agent_name ?? null);
                                }}
                                disabled={isPending}
                              >
                                <FormControl>
                                  <SelectTrigger className="h-9 text-xs">
                                    <SelectValue placeholder="Select an agent…" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {catalog.map((a) => (
                                    <SelectItem
                                      key={a.agent_id}
                                      value={a.agent_id}
                                      className="text-xs"
                                    >
                                      {a.agent_name ?? a.agent_id}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            );
                          }
                          return (
                            <FormItem className="space-y-1.5 px-1">
                              <FormLabel>Agent</FormLabel>
                              {agentSelect}
                              <FormMessage />
                            </FormItem>
                          );
                        }}
                      />
                    )}
                  </>
                )}

                {error && <p className="text-[11px] text-destructive">{error}</p>}
              </div>
            </div>

            <div className="shrink-0 flex justify-end gap-2 pt-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={isPending}
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isPending}>
                {isPending ? 'Creating…' : 'Create agent'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};
