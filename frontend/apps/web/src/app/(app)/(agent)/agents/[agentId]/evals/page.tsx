'use client';

import { parseAsStringLiteral, useQueryState } from 'nuqs';

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@workspace/ui/components/ui/tabs';
import { cn } from '@workspace/ui/lib/utils';

import { TestCasesTab } from '@/app/(app)/(agent)/_components/evals/test-cases-tab';

const EVALS_TABS = [
  { id: 'test-cases', label: 'Test Cases' },
  { id: 'eval-configs', label: 'Eval Configs', disabled: true },
  { id: 'runs', label: 'Eval Runs', disabled: true },
] as const;

type EvalsTabId = (typeof EVALS_TABS)[number]['id'];

const evalsTabIds = EVALS_TABS.map((t) => t.id);

export default function AgentEvalsPage() {
  const [tab, setTab] = useQueryState(
    'tab',
    parseAsStringLiteral(evalsTabIds).withDefault('test-cases'),
  );

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Tabs
        value={tab}
        onValueChange={(value) => setTab(value as EvalsTabId)}
        className="flex flex-col h-full"
      >
        <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0 px-4 border-b border-border">
          {EVALS_TABS.map((t) => (
            <TabsTrigger
              key={t.id}
              value={t.id}
              disabled={'disabled' in t && t.disabled}
              className={triggerClassName}
            >
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent
          value="test-cases"
          className="flex-1 flex flex-col min-h-0 mt-0"
        >
          <TestCasesTab />
        </TabsContent>

        <TabsContent
          value="eval-configs"
          className="flex-1 overflow-auto mt-0 p-4"
        >
          <div className="text-muted-foreground">
            Eval Configs — coming soon
          </div>
        </TabsContent>

        <TabsContent value="runs" className="flex-1 overflow-auto mt-0 p-4">
          <div className="text-muted-foreground">Eval Runs — coming soon</div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

const triggerClassName = cn(
  'relative cursor-pointer rounded-none bg-transparent px-5 py-3 text-sm font-medium shadow-none',
  'transition-colors duration-150 select-none',
  'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-t-full after:transition-all after:duration-150',
  'data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none data-[state=active]:after:bg-foreground',
  'data-[state=inactive]:text-muted-foreground data-[state=inactive]:after:bg-transparent',
  'hover:text-foreground hover:after:bg-border',
  'focus-visible:ring-0 focus-visible:ring-offset-0',
);
