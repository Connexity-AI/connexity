import { Platform } from '@/client/types.gen';
import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
}

function getPlatformAgentLabel(environment: EnvironmentPublic): string {
  if (environment.platform_agent_name) {
    return environment.platform_agent_name;
  }
  if (environment.platform_agent_id) {
    return environment.platform_agent_id;
  }
  return '—';
}

function getWebhookUrl(environment: EnvironmentPublic): string {
  if (environment.endpoint_url) {
    return environment.endpoint_url;
  }
  return '—';
}

function getIntegrationName(environment: EnvironmentPublic): string {
  if (environment.integration_name) {
    return environment.integration_name;
  }
  return '—';
}

const WebhookDestination: FC<Props> = ({ environment }) => {
  return (
    <div className="space-y-1">
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Webhook URL</span>
      <p className="text-xs text-foreground break-all">{getWebhookUrl(environment)}</p>
    </div>
  );
};

const RetellDestination: FC<Props> = ({ environment }) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{getIntegrationName(environment)}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Retell Agent</span>
        <span className="text-xs text-foreground">{getPlatformAgentLabel(environment)}</span>
      </div>
    </>
  );
};

const VapiDestination: FC<Props> = ({ environment }) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{getIntegrationName(environment)}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Vapi Assistant</span>
        <span className="text-xs text-foreground">{getPlatformAgentLabel(environment)}</span>
      </div>
    </>
  );
};

const ElevenLabsDestination: FC<Props> = ({ environment }) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{getIntegrationName(environment)}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          ElevenLabs Agent
        </span>
        <span className="text-xs text-foreground">{getPlatformAgentLabel(environment)}</span>
      </div>
    </>
  );
};

export const EnvironmentCardDestinationDetails: FC<Props> = ({ environment }) => {
  if (environment.platform === Platform.WEBHOOK) {
    return (
      <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
        <WebhookDestination environment={environment} />
      </div>
    );
  }
  if (environment.platform === Platform.VAPI) {
    return (
      <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
        <VapiDestination environment={environment} />
      </div>
    );
  }
  if (environment.platform === Platform.ELEVENLABS) {
    return (
      <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
        <ElevenLabsDestination environment={environment} />
      </div>
    );
  }

  return (
    <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
      <RetellDestination environment={environment} />
    </div>
  );
};
