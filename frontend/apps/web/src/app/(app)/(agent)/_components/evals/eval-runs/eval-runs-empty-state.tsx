import Link from 'next/link';
import { FlaskConical, Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { UrlGenerator } from '@/common/url-generator/url-generator';

interface EvalRunsEmptyStateProps {
  agentId: string;
}

export function EvalRunsEmptyState({ agentId }: EvalRunsEmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-accent/40">
        <FlaskConical className="h-6 w-6 text-muted-foreground/50" />
      </div>
      <div className="flex flex-col gap-1.5">
        <p className="text-sm text-foreground">No eval runs yet</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          Create an eval config and run it to see results, scores, and conversation traces here.
        </p>
      </div>
      <Button asChild size="sm" className="gap-1.5">
        <Link href={UrlGenerator.agentEvalsCreate(agentId)}>
          <Plus className="h-3.5 w-3.5" />
          Create Eval
        </Link>
      </Button>
    </div>
  );
}
