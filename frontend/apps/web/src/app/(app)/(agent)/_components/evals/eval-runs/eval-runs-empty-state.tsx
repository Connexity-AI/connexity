import { FlaskConical } from 'lucide-react';

export function EvalRunsEmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-accent/40">
        <FlaskConical className="h-6 w-6 text-muted-foreground/50" />
      </div>
      <div className="flex flex-col gap-1.5">
        <p className="text-sm text-foreground">No eval runs yet</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          Eval configs are created through your assistant. Run one to see results, scores, and
          conversation traces here.
        </p>
      </div>
    </div>
  );
}
