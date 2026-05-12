'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { useElevenlabsAgents } from '@/app/(app)/(agent)/_hooks/use-elevenlabs-agents';
import { useRetellAgents } from '@/app/(app)/(agent)/_hooks/use-retell-agents';
import { useVapiAssistants } from '@/app/(app)/(agent)/_hooks/use-vapi-assistants';
import { Platform } from '@/client/types.gen';

import type { FC } from 'react';
import type { AddEnvironmentFormValues } from './add-environment-form-schema';

interface Props {
  platform: Extract<
    AddEnvironmentFormValues['platform'],
    typeof Platform.RETELL | typeof Platform.VAPI | typeof Platform.ELEVENLABS
  >;
  integrationId: string | null;
  value: string;
  onChange: (id: string, name: string) => void;
  disabled: boolean;
}

export const AgentSelectField: FC<Props> = ({
  platform,
  integrationId,
  value,
  onChange,
  disabled,
}) => {
  const retellAgents = useRetellAgents(platform === Platform.RETELL ? integrationId : null);
  const vapiAssistants = useVapiAssistants(platform === Platform.VAPI ? integrationId : null);
  const elevenlabsAgents = useElevenlabsAgents(
    platform === Platform.ELEVENLABS ? integrationId : null
  );

  let rawAgents = elevenlabsAgents.data;
  if (platform === Platform.RETELL) {
    rawAgents = retellAgents.data;
  }
  if (platform === Platform.VAPI) {
    rawAgents = vapiAssistants.data;
  }

  let isLoading = elevenlabsAgents.isLoading;
  if (platform === Platform.RETELL) {
    isLoading = retellAgents.isLoading;
  }
  if (platform === Platform.VAPI) {
    isLoading = vapiAssistants.isLoading;
  }

  const agents = rawAgents ? dedupeAgents(rawAgents) : undefined;

  let placeholder = 'Select integration first…';
  if (isLoading) {
    placeholder = 'Loading agents…';
    if (platform === Platform.VAPI) {
      placeholder = 'Loading assistants…';
    }
  } else if (integrationId) {
    placeholder = 'Select an ElevenLabs agent…';
    if (platform === Platform.RETELL) {
      placeholder = 'Select a Retell agent…';
    }
    if (platform === Platform.VAPI) {
      placeholder = 'Select a Vapi assistant…';
    }
  }

  return (
    <Select
      value={value}
      onValueChange={(id) => {
        const selected = agents?.find((a) => a.agent_id === id);
        onChange(id, selected?.agent_name ?? id);
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
};

type AgentOption = NonNullable<ReturnType<typeof useRetellAgents>['data']>[number];

function dedupeAgents(agents: AgentOption[]): AgentOption[] {
  const byId = agents.reduce<Record<string, AgentOption>>((acc, agent) => {
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
  }, {});
  return Object.values(byId);
}
