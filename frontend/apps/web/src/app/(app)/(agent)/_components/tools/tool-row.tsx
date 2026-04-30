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
  onClick,
}: {
  name: string;
  description: string;
  url: string;
  method: HttpMethod;
  paramCount: number;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 px-5 py-4 border-b border-border cursor-pointer transition-colors group hover:bg-accent/30"
    >
      <div className="w-8 h-8 rounded-md bg-accent/60 border border-border flex items-center justify-center shrink-0">
        <Wrench className="w-3.5 h-3.5 text-muted-foreground" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm text-foreground font-mono truncate">{name || 'Untitled'}</span>
          {url && (
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
        <p className="text-xs text-muted-foreground truncate pr-4">
          {description || <span className="italic text-muted-foreground/40">No description</span>}
        </p>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {url && (
          <span className="hidden group-hover:flex items-center gap-1 text-[10px] text-muted-foreground/40 max-w-45">
            <Globe className="w-3 h-3 shrink-0" />
            <span className="truncate font-mono">{url.replace(/^https?:\/\//, '')}</span>
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
