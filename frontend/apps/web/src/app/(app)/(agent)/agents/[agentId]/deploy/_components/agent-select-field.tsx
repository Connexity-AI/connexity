'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { useRetellAgents } from '@/app/(app)/(agent)/_hooks/use-retell-agents';

import type { FC } from 'react';

interface Props {
  integrationId: string | null;
  value: string;
  onChange: (id: string, name: string) => void;
  disabled: boolean;
}

export const AgentSelectField: FC<Props> = ({ integrationId, value, onChange, disabled }) => {
  const { data: rawAgents, isLoading } = useRetellAgents(integrationId);
  const agents = rawAgents ? dedupeAgents(rawAgents) : undefined;

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

type RetellAgent = NonNullable<ReturnType<typeof useRetellAgents>['data']>[number];

function dedupeAgents(agents: RetellAgent[]): RetellAgent[] {
  const byId = agents.reduce<Record<string, RetellAgent>>((acc, agent) => {
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
