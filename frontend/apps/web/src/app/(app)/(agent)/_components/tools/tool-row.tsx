import { ChevronRight, Globe, Wrench } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { HttpMethod } from '@/app/(app)/(agent)/_schemas/agent-form';

const METHOD_COLOR: Record<HttpMethod, string> = {
  GET: 'text-green-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-400',
  PATCH: 'text-purple-400',
  DELETE: 'text-red-400',
};

const METHOD_BG: Record<HttpMethod, string> = {
  GET: 'bg-green-500/10 border-green-500/20',
  POST: 'bg-blue-500/10 border-blue-500/20',
  PUT: 'bg-amber-500/10 border-amber-500/20',
  PATCH: 'bg-purple-500/10 border-purple-500/20',
  DELETE: 'bg-red-500/10 border-red-500/20',
};

export function ToolRow({
  name,
  description,
  url,
  method,
  paramCount,
  isDefault,
  onClick,
}: {
  name: string;
  description: string;
  url: string;
  method: HttpMethod;
  paramCount: number;
  isDefault?: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="flex w-full max-w-full min-w-0 items-center gap-4 overflow-hidden px-5 py-4 border-b border-border cursor-pointer transition-colors group hover:bg-accent/30"
    >
      <div className="w-8 h-8 rounded-md bg-accent/60 border border-border flex items-center justify-center shrink-0">
        <Wrench className="w-3.5 h-3.5 text-muted-foreground" />
      </div>

      <div className="w-0 flex-1 min-w-0">
        <div className="mb-0.5 flex w-full min-w-0 items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-sm text-foreground font-mono">
            {name || 'Untitled'}
          </span>
          {!isDefault && url && (
            <span
              className={cn(
                'text-[10px] px-1.5 py-0.5 rounded border font-mono shrink-0',
                METHOD_BG[method],
                METHOD_COLOR[method]
              )}
            >
              {method}
            </span>
          )}
        </div>
        <p className="w-full min-w-0 truncate pr-4 text-xs text-muted-foreground">
          {description || <span className="italic text-muted-foreground/40">No description</span>}
        </p>
      </div>

      <div className="ml-auto flex min-w-0 items-center gap-3">
        {!isDefault && url && (
          <span className="hidden min-w-0 max-w-45 overflow-hidden items-center gap-1 text-[10px] text-muted-foreground/40 group-hover:flex">
            <Globe className="w-3 h-3 shrink-0" />
            <span className="min-w-0 truncate font-mono">{url.replace(/^https?:\/\//, '')}</span>
          </span>
        )}
        {paramCount > 0 && (
          <span className="text-[10px] text-muted-foreground/40 tabular-nums">
            {paramCount} param{paramCount !== 1 ? 's' : ''}
          </span>
        )}
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/20 group-hover:text-muted-foreground/60 transition-colors" />
      </div>
    </div>
  );
}
