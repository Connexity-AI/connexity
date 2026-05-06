'use client';

import { useMemo, useState } from 'react';

import { Check, ChevronDown, Loader2, Webhook } from 'lucide-react';

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
import { getWebhookPayloadPreview } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/get-webhook-payload-preview';
import { AgentSelectField } from './agent-select-field';
import { EvalGateFormSection } from './eval-gate-form-section';

import type { FC } from 'react';
import type { IntegrationPublic } from '@/client/types.gen';

interface Props {
  agentId: string;
  integrations: IntegrationPublic[];
  onCancel: () => void;
  onSuccess: () => void;
}

export const AddEnvironmentForm: FC<Props> = ({ agentId, integrations, onCancel, onSuccess }) => {
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
  } = useAddEnvironmentForm({ agentId, onSuccess });
  const [payloadOpen, setPayloadOpen] = useState(false);
  const name = form.watch('name');
  const payloadPreview = useMemo(
    () => getWebhookPayloadPreview({ environmentName: name }),
    [name]
  );

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
                  className={cn(
                    'flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all',
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
                </button>
                <button
                  type="button"
                  className={cn(
                    'flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border text-left transition-all',
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
                </button>
              </div>
            </div>

            {platform === 'retell' && (
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
                          {integrations.length === 0 && (
                            <div className="px-3 py-2 text-xs text-muted-foreground">
                              No Retell integrations found
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
                      <FormLabel>Agent</FormLabel>
                      <FormControl>
                        <AgentSelectField
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
                        We send a POST request with JSON payload. Any 2xx response means success.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="rounded-lg border border-border overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setPayloadOpen((open) => !open)}
                    className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-accent/30 transition-colors"
                  >
                    <span className="text-[11px] text-muted-foreground">Payload preview</span>
                    <ChevronDown
                      className={cn(
                        'w-3.5 h-3.5 text-muted-foreground transition-transform',
                        payloadOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  {payloadOpen && (
                    <div className="px-3 pb-3 border-t border-border">
                      <div className="rounded-md bg-muted/30 border border-border overflow-hidden mt-2">
                        <pre className="text-[10px] text-muted-foreground font-mono px-3 py-2.5 overflow-auto max-h-44 leading-relaxed">
                          {payloadPreview}
                        </pre>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1.5">
                        Sent as <code className="text-foreground/70">POST</code> with{' '}
                        <code className="text-foreground/70">Content-Type: application/json</code>
                      </p>
                    </div>
                  )}
                </div>
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
              'Add environment'
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
};
