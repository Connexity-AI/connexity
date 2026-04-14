'use client';

import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { GitBranch, Loader2, Upload } from 'lucide-react';

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from '@workspace/ui/components/ui/breadcrumb';
import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { EditableBreadcrumbName } from '@/app/(app)/(agent)/_components/header/editable-breadcrumb-name';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useDelayedFlag } from '@/app/(app)/(agent)/_hooks/use-delayed-flag';
import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { PlatformHeader } from '@/components/common/platform-header';

export function AgentEditHeader() {
  return (
    <PlatformHeader
      className="px-6"
      leading={<AgentEditBreadcrumb />}
      trailing={<AgentEditActions />}
    />
  );
}

function AgentEditBreadcrumb() {
  const { agentName, agentId } = useAgentEditFormActions();

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

          <EditableBreadcrumbName agentId={agentId} agentName={agentName} />
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );
}

function AgentEditActions() {
  const { onSubmit, isPending, isReadOnly, isDraftSaving } =
    useAgentEditFormActions();
  const { openDrawer } = useVersions();
  const showSaving = useDelayedFlag(isDraftSaving, 300);

  return (
    <div className="flex items-center gap-2">
      {showSaving && (
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Saving...
        </span>
      )}

      <Button
        variant="outline"
        icon={GitBranch}
        size="sm"
        className="gap-1.5"
        onClick={openDrawer}
      />

      <Button
        size="sm"
        className="gap-1.5"
        onClick={onSubmit}
        disabled={isPending || isReadOnly}
      >
        <Upload className="w-3.5 h-3.5" />
        {isPending ? 'Publishing...' : 'Publish'}
      </Button>
    </div>
  );
}
