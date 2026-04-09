'use client';

import { use } from 'react';

import { useFormContext } from 'react-hook-form';

import { Tabs, TabsList, TabsTrigger } from '@workspace/ui/components/ui/tabs';
import { cn } from '@workspace/ui/lib/utils';
import { parseAsStringLiteral, useQueryState } from 'nuqs';

import { AgentEditHeader } from '@/app/(app)/(agent)/_components/agent-edit-header';
import { PromptTab } from '@/app/(app)/(agent)/_components/prompt-tab';
import { SettingsTab } from '@/app/(app)/(agent)/_components/settings-tab';
import { ToolsTab } from '@/app/(app)/(agent)/_components/tools-tab';
import { VersionsDrawer } from '@/app/(app)/(agent)/_components/versions-drawer';
import { PublishDialog } from '@/app/(app)/(agent)/_components/publish-dialog';
import { ReadOnlyBanner } from '@/app/(app)/(agent)/_components/read-only-banner';
import { TABS, type TabId } from '@/app/(app)/(agent)/_constants/agent';
import { AgentEditFormProvider } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { VersionsProvider } from '@/app/(app)/(agent)/_context/versions-context';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import type { FC } from 'react';

const TAB_FIELDS: Record<TabId, (keyof AgentFormValues)[]> = {
  prompt: ['prompt'],
  tools: ['tools'],
  settings: ['provider', 'model', 'temperature'],
};

interface Props {
  params: Promise<{ agentId: string }>;
}

const tabIds = TABS.map((t) => t.id);

const AgentPage: FC<Props> = ({ params }) => {
  const { agentId } = use(params);
  const [tab, setTab] = useQueryState(
    'tab',
    parseAsStringLiteral(tabIds).withDefault('prompt'),
  );

  return (
    <VersionsProvider>
      <AgentEditFormProvider agentId={agentId}>
        <AgentEditHeader />

        <ReadOnlyBanner />

        <main className="flex-1 flex flex-col">
          <Tabs value={tab} onValueChange={(v) => setTab(v as TabId)} className="flex flex-col h-full">
            <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0 px-4 border-b border-border">
              {TABS.map((t) => (
                <AgentTabTrigger key={t.id} tab={t} />
              ))}
            </TabsList>

            <PromptTab />

            <ToolsTab />

            <SettingsTab />
          </Tabs>
        </main>

        <VersionsDrawer />
        <PublishDialog />
      </AgentEditFormProvider>
    </VersionsProvider>
  );
};

export default AgentPage;

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
