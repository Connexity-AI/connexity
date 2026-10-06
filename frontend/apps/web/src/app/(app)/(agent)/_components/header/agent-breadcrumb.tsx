'use client';

import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@workspace/ui/components/ui/breadcrumb';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';

interface AgentBreadcrumbProps {
  agentId: string;
}

export function AgentBreadcrumb({ agentId }: AgentBreadcrumbProps) {
  const { data: agent } = useAgent(agentId);

  return (
    <div className="flex items-center gap-3">
      <SidebarTrigger />

      <Separator orientation="vertical" className="h-5" />

      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={UrlGenerator.agents()}>Agents</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>

          <BreadcrumbSeparator />

          <BreadcrumbItem>
            <BreadcrumbPage>{agent?.name ?? ''}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );
}
