'use client';

import { AlertTriangle, ListChecks, Loader2, RefreshCw } from 'lucide-react';
import { Badge } from '@workspace/ui/components/ui/badge';
import { Button } from '@workspace/ui/components/ui/button';
import { Skeleton } from '@workspace/ui/components/ui/skeleton';
import { TabsContent } from '@workspace/ui/components/ui/tabs';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAgentRequirements } from '@/app/(app)/(agent)/_hooks/use-agent-requirements';
import { useReextractRequirements } from '@/app/(app)/(agent)/_hooks/use-reextract-requirements';

import type { RequirementPublic } from '@/client/types.gen';

const TAB_VALUE = 'requirements';

export function RequirementsTab() {
  const { agentId } = useAgentEditFormActions();
  const { data, isLoading } = useAgentRequirements(agentId);
  const { reextract, isPending } = useReextractRequirements(agentId);

  const requirements = data?.data ?? [];
  const status = data?.status ?? 'pending';
  const isExtracting = isPending || status === 'extracting';

  return (
    <TabsContent
      value={TAB_VALUE}
      className="flex-1 mt-0 flex flex-col min-h-0 overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">
            {requirements.length} requirement{requirements.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-xs text-muted-foreground/60">
            Auto-extracted · read-only
          </p>
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 h-7 text-xs"
            onClick={() => reextract()}
            disabled={isExtracting}
          >
            {isExtracting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
            {requirements.length > 0 ? 'Re-extract' : 'Extract'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <RequirementsSkeleton />
        ) : isExtracting ? (
          <ExtractingState />
        ) : status === 'failed' ? (
          <FailedState />
        ) : requirements.length === 0 ? (
          <EmptyState status={status} />
        ) : (
          <ul className="divide-y divide-border">
            {requirements.map((requirement, index) => (
              <RequirementRow
                key={requirement.id}
                requirement={requirement}
                index={index + 1}
              />
            ))}
          </ul>
        )}
      </div>
    </TabsContent>
  );
}

function RequirementRow({
  requirement,
  index,
}: {
  requirement: RequirementPublic;
  index: number;
}) {
  return (
    <li className="flex gap-3 px-5 py-3">
      <span className="text-xs text-muted-foreground/50 tabular-nums pt-0.5 w-5 shrink-0">
        {index}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground">{requirement.text}</p>
        <div className="flex items-center gap-2 mt-1">
          {requirement.category ? (
            <Badge variant="secondary" className="text-[10px] py-0 px-1.5 h-4">
              {requirement.category}
            </Badge>
          ) : null}
          {requirement.source_ref ? (
            <span className="text-[10px] text-muted-foreground/60 truncate">
              {requirement.source_ref}
            </span>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function ExtractingState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-5 py-12 text-center">
      <Loader2 className="w-5 h-5 text-muted-foreground/40 animate-spin" />
      <p className="text-xs text-muted-foreground/60 max-w-xs">
        Extracting requirements from the agent… this usually takes a few seconds.
      </p>
    </div>
  );
}

function FailedState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-5 py-12 text-center">
      <AlertTriangle className="w-5 h-5 text-destructive/70" />
      <p className="text-xs text-muted-foreground/70 max-w-xs">
        Requirement extraction failed — this is usually a temporary LLM error or a
        missing API key. Use the Re-extract button above to try again.
      </p>
    </div>
  );
}

function EmptyState({ status }: { status: string }) {
  // `empty` = extraction ran and found nothing; `pending` = not yet attempted.
  const message =
    status === 'empty'
      ? 'No requirements were extracted from this agent. If that seems wrong, try Re-extract above.'
      : 'No requirements yet. They are extracted automatically when an agent is imported or a version is published — or trigger it with Extract above.';
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-5 py-12 text-center">
      <ListChecks className="w-5 h-5 text-muted-foreground/40" />
      <p className="text-xs text-muted-foreground/60 max-w-xs">{message}</p>
    </div>
  );
}

function RequirementsSkeleton() {
  return (
    <div className="px-5 py-3 space-y-4">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="flex gap-3">
          <Skeleton className="h-4 w-4 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}
