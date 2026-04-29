'use client';

import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { FlaskConical, Pencil, Radio, Rocket } from 'lucide-react';

import { Tabs, TabsList, TabsTrigger } from '@workspace/ui/components/ui/tabs';

import type { LucideIcon } from 'lucide-react';

export type AgentPageMode = 'edit' | 'evals' | 'deploy' | 'observe';

interface ModeTab {
  value: AgentPageMode;
  label: string;
  Icon: LucideIcon;
  href: (agentId: string) => string;
  disabled?: boolean;
}

const MODE_TABS: ModeTab[] = [
  { value: 'edit', label: 'Edit', Icon: Pencil, href: UrlGenerator.agentEdit },
  { value: 'evals', label: 'Evals', Icon: FlaskConical, href: UrlGenerator.agentEvals },
  {
    value: 'deploy',
    label: 'Deploy',
    Icon: Rocket,
    href: UrlGenerator.agentDeploy,
  },
  {
    value: 'observe',
    label: 'Observe',
    Icon: Radio,
    href: UrlGenerator.agentObserve,
  },
];

interface AgentModeTabsProps {
  agentId: string;
  activeMode: AgentPageMode;
}

export function AgentModeTabs({ agentId, activeMode }: AgentModeTabsProps) {
  return (
    <Tabs value={activeMode}>
      <TabsList>
        {MODE_TABS.map(({ value, label, Icon, href, disabled }) => (
          <TabsTrigger
            key={value}
            value={value}
            disabled={disabled}
            asChild={!disabled}
            className="gap-1.5 px-4  cursor-pointer disabled:cursor-not-allowed"
          >
            {disabled ? (
              <>
                <Icon className="h-3.5 w-3.5" />
                {label}
              </>
            ) : (
              <Link href={href(agentId)}>
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Link>
            )}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
