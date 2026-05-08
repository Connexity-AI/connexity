'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { useRetellAgents } from '@/app/(app)/(agent)/_hooks/use-retell-agents';
import { useVapiAssistants } from '@/app/(app)/(agent)/_hooks/use-vapi-assistants';

import type { FC } from 'react';
import type { AddEnvironmentFormValues } from './add-environment-form-schema';

interface Props {
  platform: Extract<AddEnvironmentFormValues['platform'], 'retell' | 'vapi'>;
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
  const retellAgents = useRetellAgents(platform === 'retell' ? integrationId : null);
  const vapiAssistants = useVapiAssistants(platform === 'vapi' ? integrationId : null);
  const rawAgents = platform === 'retell' ? retellAgents.data : vapiAssistants.data;
  const isLoading = platform === 'retell' ? retellAgents.isLoading : vapiAssistants.isLoading;
  const agents = rawAgents ? dedupeAgents(rawAgents) : undefined;

  let placeholder = 'Select integration first…';
  if (isLoading) {
    placeholder = platform === 'retell' ? 'Loading agents…' : 'Loading assistants…';
  } else if (integrationId) {
    placeholder = platform === 'retell' ? 'Select a Retell agent…' : 'Select a Vapi assistant…';
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
