'use client';

import { useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import { Check, Loader2, Webhook } from 'lucide-react';

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
import { cn } from '@workspace/ui/lib/utils';

import { useAddEnvironmentForm } from '@/app/(app)/(agent)/_hooks/use-add-environment-form';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';
import { webhookPayloadPreviewQuery } from '@/app/(app)/(agent)/_queries/webhook-payload-preview-query';
import { AgentSelectField } from './agent-select-field';
import { EvalGateFormSection } from './eval-gate-form-section';
import { PayloadPreviewSection } from './payload-preview-section';

import type { FC } from 'react';
import type { EnvironmentPublic, IntegrationPublic } from '@/client/types.gen';

interface Props {
  agentId: string;
  integrations: IntegrationPublic[];
  environment: EnvironmentPublic | null;
  onCancel: () => void;
  onSuccess: () => void;
}

export const AddEnvironmentForm: FC<Props> = ({
  agentId,
  integrations,
  environment,
  onCancel,
  onSuccess,
}) => {
  const {
    form,
    onSubmit,
    platform,
    integrationId,
    handlePlatformChange,
    handleIntegrationChange,
    handleAgentChange,
    isPending,
    error,
  } = useAddEnvironmentForm({ agentId, environment, onSuccess });
  const [payloadOpen, setPayloadOpen] = useState(false);
  const isEditing = environment !== null;
  const submitLabel = isEditing ? 'Save changes' : 'Add environment';
  const name = form.watch('name');
  const evalGateEnabled = form.watch('eval_gate_enabled');
  const evalGateEvalConfigId = form.watch('eval_gate_eval_config_id');
  const environmentNameForPreview = name.trim() || 'production';
  const platformIntegrations = integrations.filter((integration) => integration.provider === platform);
  const integrationEmptyLabel =
    platform === 'vapi' ? 'No Vapi integrations found' : 'No Retell integrations found';
  const agentLabel = platform === 'vapi' ? 'Assistant' : 'Agent';
  const { data: agentVersionsData, isLoading: isAgentVersionsLoading } = useAgentVersions(agentId);
  const hasPublishedAgentVersion =
    (agentVersionsData?.count ?? agentVersionsData?.data.length ?? 0) > 0;
  const showMissingPublishedVersionInfo = !isAgentVersionsLoading && !hasPublishedAgentVersion;
  const {
    data: payloadPreviewData,
    isLoading: isPayloadPreviewLoading,
    isError: isPayloadPreviewError,
    error: payloadPreviewError,
  } = useQuery({
      ...webhookPayloadPreviewQuery({
        agentId,
        environmentName: environmentNameForPreview,
        evalGateEvalConfigId: evalGateEnabled ? evalGateEvalConfigId : null,
      }),
      enabled: platform === 'webhook' && hasPublishedAgentVersion,
    });
  const payloadPreviewErrorMessage =
    payloadPreviewError instanceof Error
      ? payloadPreviewError.message
      : 'unable to load payload preview right now';
  const payloadPreview = isPayloadPreviewError
    ? payloadPreviewErrorMessage
    : JSON.stringify(payloadPreviewData ?? {}, null, 2);

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
              <div className="grid grid-cols-3 gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  className={cn(
                    'h-auto flex-col items-start justify-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all cursor-pointer whitespace-normal',
                    platform === 'retell'
                      ? 'border-foreground/40 bg-accent'
                      : 'border-border hover:bg-accent/40'
                  )}
                  onClick={() => handlePlatformChange('retell')}
                  disabled={isPending}
                >
                  <span className="text-xs text-foreground">Retell</span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    Push directly via Retell API (requires integration)
                  </span>
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className={cn(
                    'h-auto flex-col items-start justify-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all cursor-pointer whitespace-normal',
                    platform === 'vapi'
                      ? 'border-foreground/40 bg-accent'
                      : 'border-border hover:bg-accent/40'
                  )}
                  onClick={() => handlePlatformChange('vapi')}
                  disabled={isPending}
                >
                  <span className="text-xs text-foreground">Vapi</span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    Push directly via Vapi API (requires integration)
                  </span>
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className={cn(
                    'h-auto flex-col items-start justify-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all cursor-pointer whitespace-normal',
                    platform === 'webhook'
                      ? 'border-foreground/40 bg-accent'
                      : 'border-border hover:bg-accent/40'
                  )}
                  onClick={() => handlePlatformChange('webhook')}
                  disabled={isPending}
                >
                  <span className="text-xs text-foreground">Webhook</span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    Send deployment payload to your custom endpoint
                  </span>
                </Button>
              </div>
            </div>

            {(platform === 'retell' || platform === 'vapi') && (
              <>
                <FormField
                  control={form.control}
                  name="integration_id"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel>Integration</FormLabel>
                      <Select
                        value={field.value ?? undefined}
                        onValueChange={handleIntegrationChange}
                        disabled={isPending}
                      >
                        <FormControl>
                          <SelectTrigger className="h-9 text-xs">
                            <SelectValue placeholder="Select an integration…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {platformIntegrations.map((i) => (
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
                          {platformIntegrations.length === 0 && (
                            <div className="px-3 py-2 text-xs text-muted-foreground">
                              {integrationEmptyLabel}
                            </div>
                          )}
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
                      <FormLabel>{agentLabel}</FormLabel>
                      <FormControl>
                        <AgentSelectField
                          platform={platform}
                          integrationId={integrationId || null}
                          value={field.value ?? ''}
                          onChange={handleAgentChange}
                          disabled={isPending}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            {platform === 'webhook' && (
              <>
                <FormField
                  control={form.control}
                  name="endpoint_url"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel htmlFor="endpoint-url">Webhook URL</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Webhook className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                          <Input
                            id="endpoint-url"
                            placeholder="https://your-server.com/deploy/:agent_id"
                            className="pl-8"
                            value={field.value ?? ''}
                            onChange={(event) =>
                              field.onChange(event.target.value.trim() || null)
                            }
                            disabled={isPending}
                          />
                        </div>
                      </FormControl>
                      <p className="text-[11px] text-muted-foreground">
                        We POST to this URL on deploy. A 200 response is a success; any other
                        status is treated as a failure and the response body will be shown.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <PayloadPreviewSection
                  showMissingPublishedVersionInfo={showMissingPublishedVersionInfo}
                  payloadOpen={payloadOpen}
                  onTogglePayloadOpen={() => setPayloadOpen((open) => !open)}
                  payloadPreview={payloadPreview}
                  isPayloadPreviewLoading={isPayloadPreviewLoading}
                />
              </>
            )}

            <EvalGateFormSection agentId={agentId} disabled={isPending} />
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
              submitLabel
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
};
