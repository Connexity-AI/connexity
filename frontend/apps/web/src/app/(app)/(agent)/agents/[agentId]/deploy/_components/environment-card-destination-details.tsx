import { Platform } from '@/client/types.gen';
import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useIntegrations } from '@/app/(app)/(agent)/_hooks/use-integrations';
import type { AgentCanonicalDeployTarget } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_utils/agent-canonical-deploy-target';
import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  agentId: string;
  environment: EnvironmentPublic;
}

function getPlatformAgentLabel(
  platformAgentName: string | null | undefined,
  platformAgentId: string | null | undefined
): string {
  if (platformAgentName) {
    return platformAgentName;
  }
  if (platformAgentId) {
    return platformAgentId;
  }
  return '—';
}

function getWebhookUrl(environment: EnvironmentPublic): string {
  if (environment.endpoint_url) {
    return environment.endpoint_url;
  }
  return '—';
}

function getIntegrationName(
  integrationId: string | null | undefined,
  integrationNameMap: Map<string, string>
): string {
  if (integrationId) {
    return integrationNameMap.get(integrationId) ?? integrationId;
  }
  return '—';
}

const WebhookDestination: FC<{ environment: EnvironmentPublic }> = ({ environment }) => {
  return (
    <div className="space-y-1">
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Webhook URL</span>
      <p className="text-xs text-foreground break-all">{getWebhookUrl(environment)}</p>
    </div>
  );
};

const RetellDestination: FC<{
  integrationName: string;
  platformAgentLabel: string;
}> = ({ integrationName, platformAgentLabel }) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{integrationName}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Retell Agent</span>
        <span className="text-xs text-foreground">{platformAgentLabel}</span>
      </div>
    </>
  );
};

const VapiDestination: FC<{ integrationName: string; platformAgentLabel: string }> = ({
  integrationName,
  platformAgentLabel,
}) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{integrationName}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Vapi Assistant</span>
        <span className="text-xs text-foreground">{platformAgentLabel}</span>
      </div>
    </>
  );
};

const ElevenLabsDestination: FC<{
  integrationName: string;
  platformAgentLabel: string;
}> = ({ integrationName, platformAgentLabel }) => {
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Integration</span>
        <span className="text-xs text-foreground">{integrationName}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          ElevenLabs Agent
        </span>
        <span className="text-xs text-foreground">{platformAgentLabel}</span>
      </div>
    </>
  );
};

export const EnvironmentCardDestinationDetails: FC<Props> = ({ agentId, environment }) => {
  const { data: agent } = useAgent(agentId);
  const agentTarget = agent as AgentCanonicalDeployTarget | undefined;
  const { data: integrationsData } = useIntegrations();
  const integrationNameMap = new Map(
    integrationsData?.data.map((integration) => [integration.id, integration.name]) ?? []
  );
  const integrationName = getIntegrationName(agentTarget?.integration_id, integrationNameMap);
  const platformAgentLabel = getPlatformAgentLabel(
    agentTarget?.platform_agent_name,
    agentTarget?.platform_agent_id
  );
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
        <VapiDestination
          integrationName={integrationName}
          platformAgentLabel={platformAgentLabel}
        />
      </div>
    );
  }
  if (environment.platform === Platform.ELEVENLABS) {
    return (
      <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
        <ElevenLabsDestination
          integrationName={integrationName}
          platformAgentLabel={platformAgentLabel}
        />
      </div>
    );
  }

  return (
    <div className="px-5 py-4 border-b border-border bg-accent/5 space-y-3">
      <RetellDestination
        integrationName={integrationName}
        platformAgentLabel={platformAgentLabel}
      />
    </div>
  );
};
