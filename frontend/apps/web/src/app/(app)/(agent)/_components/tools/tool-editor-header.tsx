import { ArrowLeft, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface ToolEditorHeaderProps {
  toolName: string;
  isNew: boolean;
  onBack: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}

export function ToolEditorHeader({
  toolName,
  isNew,
  onBack,
  onDelete,
  readOnly,
}: ToolEditorHeaderProps) {
  return (
    <div className="flex items-center justify-between px-5 h-13 border-b border-border shrink-0 gap-4">
      <Button
        variant="ghost"
        onClick={onBack}
        className="h-auto p-0 font-normal flex items-center gap-2 text-muted-foreground hover:text-foreground hover:bg-transparent transition-colors group shrink-0"
      >
        <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
        <span className="text-xs">Tools</span>
      </Button>

      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="text-sm text-foreground truncate">
          {toolName || (isNew ? 'New Tool' : 'Untitled')}
        </span>

        {isNew && (
          <span className="text-[10px] bg-blue-500/15 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded shrink-0">
            new
          </span>
        )}
      </div>

      {!isNew && !readOnly && (
        <Button
          variant="ghost"
          onClick={onDelete}
          className="h-auto p-0 font-normal flex items-center gap-1.5 text-xs text-red-400/60 hover:text-red-400 hover:bg-transparent transition-colors shrink-0"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </Button>
      )}
    </div>
  );
}
