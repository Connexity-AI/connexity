import { Plus, Wrench } from 'lucide-react';
import { Button } from '@workspace/ui/components/ui/button';

export function ToolsEmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
      <div className="w-14 h-14 rounded-2xl border border-border bg-accent/40 flex items-center justify-center">
        <Wrench className="w-6 h-6 text-muted-foreground/50" />
      </div>
      <div className="flex flex-col gap-1.5">
        <p className="text-sm text-foreground">No tools yet</p>
        <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
          Add custom tool calls that your agent can invoke during conversations. The model uses the
          tool name and description to decide when to call each one.
        </p>
      </div>
      <Button size="sm" className="gap-2" onClick={onAdd}>
        <Plus className="w-3.5 h-3.5" />
        Add tool
      </Button>
    </div>
  );
}
