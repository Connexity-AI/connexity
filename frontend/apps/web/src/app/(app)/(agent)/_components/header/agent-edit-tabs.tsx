'use client';

import { useFormContext } from 'react-hook-form';
import { parseAsStringLiteral, useQueryState } from 'nuqs';

import { Tabs, TabsList, TabsTrigger } from '@workspace/ui/components/ui/tabs';
import { cn } from '@workspace/ui/lib/utils';

import { PromptTab } from '@/app/(app)/(agent)/_components/prompt/prompt-tab';
import { SettingsTab } from '@/app/(app)/(agent)/_components/settings/settings-tab';
import { ToolsTab } from '@/app/(app)/(agent)/_components/tools/tools-tab';
import { TABS, type TabId } from '@/app/(app)/(agent)/_constants/agent';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const TAB_FIELDS: Record<TabId, (keyof AgentFormValues)[]> = {
  prompt: ['prompt'],
  tools: ['tools'],
  settings: ['provider', 'model', 'temperature'],
};

const tabIds = TABS.map((tabDefinition) => tabDefinition.id);

export function AgentEditTabs() {
  const [tab, setTab] = useQueryState(
    'tab',
    parseAsStringLiteral(tabIds).withDefault('prompt'),
  );

  return (
    <main className="flex-1 flex flex-col min-w-0">
      <Tabs
        value={tab}
        onValueChange={(value) => setTab(value as TabId)}
        className="flex flex-col h-full"
      >
        <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0 px-4 border-b border-border">
          {TABS.map((tabDefinition) => (
            <AgentTabTrigger key={tabDefinition.id} tab={tabDefinition} />
          ))}
        </TabsList>

        <PromptTab />

        <ToolsTab />

        <SettingsTab />
      </Tabs>
    </main>
  );
}

function AgentTabTrigger({ tab }: { tab: (typeof TABS)[number] }) {
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
  'relative rounded-none bg-transparent px-5 py-3 text-sm font-medium shadow-none',
  'transition-colors duration-150 select-none',
  'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-t-full after:transition-all after:duration-150',
  'data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none data-[state=active]:after:bg-foreground',
  'data-[state=inactive]:text-muted-foreground data-[state=inactive]:after:bg-transparent',
  'hover:text-foreground hover:after:bg-border',
  'focus-visible:ring-0 focus-visible:ring-offset-0'
);
