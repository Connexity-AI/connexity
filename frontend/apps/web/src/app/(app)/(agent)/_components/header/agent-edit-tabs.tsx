'use client';

import { useFormContext } from 'react-hook-form';
import { parseAsString, useQueryState } from 'nuqs';

import { Tabs, TabsList, TabsTrigger } from '@workspace/ui/components/ui/tabs';
import { cn } from '@workspace/ui/lib/utils';

import { InfoTab } from '@/app/(app)/(agent)/_components/info/info-tab';
import { PromptTab } from '@/app/(app)/(agent)/_components/prompt/prompt-tab';
import { RequirementsTab } from '@/app/(app)/(agent)/_components/requirements/requirements-tab';
import { SettingsTab } from '@/app/(app)/(agent)/_components/settings/settings-tab';
import { ToolsTab } from '@/app/(app)/(agent)/_components/tools/tools-tab';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import {
  defaultTabForAgent,
  visibleTabsForAgent,
  type TabId,
} from '@/app/(app)/(agent)/_constants/agent';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const TAB_FIELDS: Record<TabId, (keyof AgentFormValues)[]> = {
  prompt: ['prompt'],
  info: [],
  requirements: [],
  tools: ['tools'],
  settings: ['provider', 'model', 'temperature'],
};

export function AgentEditTabs() {
  const { agent } = useAgentEditFormActions();
  const [rawTab, setTab] = useQueryState('tab', parseAsString);

  const tabs = visibleTabsForAgent(agent);
  // Resolve the active tab against the agent's visible set: an out-of-range or
  // missing ?tab (e.g. ?tab=prompt on a flow agent) falls back to the default.
  const activeTab: TabId =
    tabs.find((tab) => tab.id === rawTab)?.id ?? defaultTabForAgent(agent);

  return (
    <main className="flex-1 flex flex-col min-w-0">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setTab(value)}
        className="flex flex-col h-full"
      >
        <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0 px-4 border-b border-border">
          {tabs.map((tabDefinition) => (
            <AgentTabTrigger key={tabDefinition.id} tab={tabDefinition} />
          ))}
        </TabsList>

        <ActiveTabContent tab={activeTab} />
      </Tabs>
    </main>
  );
}

function ActiveTabContent({ tab }: { tab: TabId }) {
  if (tab === 'info') {
    return <InfoTab />;
  }

  if (tab === 'requirements') {
    return <RequirementsTab />;
  }

  if (tab === 'tools') {
    return <ToolsTab />;
  }

  if (tab === 'settings') {
    return <SettingsTab />;
  }

  return <PromptTab />;
}

function AgentTabTrigger({ tab }: { tab: { id: TabId; label: string } }) {
  const { formState: { errors } } = useFormContext<AgentFormValues>();
  const hasError = TAB_FIELDS[tab.id]?.some((field) => field in errors);

  return (
    <TabsTrigger
      value={tab.id}
      className={cn(
        triggerClassName,
        hasError &&
          'text-destructive data-[state=active]:text-destructive data-[state=inactive]:text-destructive hover:text-destructive',
      )}
    >
      {tab.label}
    </TabsTrigger>
  );
}

const triggerClassName = cn(
  'relative cursor-pointer rounded-none bg-transparent px-5 py-3 text-sm font-medium shadow-none',
  'transition-colors duration-150 select-none',
  'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-t-full after:transition-all after:duration-150',
  'data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none data-[state=active]:after:bg-foreground',
  'data-[state=inactive]:text-muted-foreground data-[state=inactive]:after:bg-transparent',
  'hover:text-foreground hover:after:bg-border',
  'focus-visible:ring-0 focus-visible:ring-offset-0'
);
