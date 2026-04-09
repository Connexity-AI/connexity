import { ArrowLeft } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface DraftToolEditorHeaderProps {
  toolName: string;
  onBack: () => void;
  onSave: () => void;
}

export function DraftToolEditorHeader({ toolName, onBack, onSave }: DraftToolEditorHeaderProps) {
  return (
    <div className="flex items-center justify-between px-5 h-[52px] border-b border-border shrink-0 gap-4">
      <Button
        variant="ghost"
        onClick={onBack}
        className="h-auto p-0 font-normal flex items-center gap-2 text-muted-foreground hover:text-foreground hover:bg-transparent transition-colors group shrink-0"
      >
        <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
        <span className="text-xs">Tools</span>
      </Button>

      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="text-sm text-foreground truncate">{toolName || 'New Tool'}</span>
        <span className="text-[10px] bg-blue-500/15 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded shrink-0">
          new
        </span>
      </div>

      <Button size="sm" className="h-7 text-xs shrink-0" onClick={onSave}>
        Add tool
      </Button>
    </div>
  );
}
