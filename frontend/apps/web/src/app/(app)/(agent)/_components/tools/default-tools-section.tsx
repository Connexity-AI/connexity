'use client';

import { Plus, Wrench } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';

import { ToolRow } from '@/app/(app)/(agent)/_components/tools/tool-row';
import { useDefaultToolTemplates } from '@/app/(app)/(agent)/_hooks/use-default-tool-templates';

import type { DefaultToolTemplate } from '@/app/(app)/(agent)/_queries/default-tool-templates-query';
import type { AgentToolValues } from '@/app/(app)/(agent)/_schemas/agent-form';

interface DefaultToolsSectionProps {
  defaultTools: { tool: AgentToolValues; index: number }[];
  isReadOnly: boolean;
  onAddDefault: (template: DefaultToolTemplate) => void;
  onOpenExisting: (index: number) => void;
}

export function DefaultToolsSection({
  defaultTools,
  isReadOnly,
  onAddDefault,
  onOpenExisting,
}: DefaultToolsSectionProps) {
  const { data: templates = [], isLoading } = useDefaultToolTemplates();

  const availableTemplates = templates.filter(
    (template) => !defaultTools.some((entry) => entry.tool.name === template.name)
  );

  return (
    <div className="border-b border-border">
      <div className="flex items-center justify-between px-5 py-3 bg-accent/5">
        <div className="flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5 text-muted-foreground/60" />
          <span className="text-xs text-muted-foreground uppercase tracking-wider">
            Default Tools
          </span>
        </div>
        {!isReadOnly && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 h-7 text-xs"
                disabled={isLoading || availableTemplates.length === 0}
              >
                <Plus className="w-3 h-3" />
                Add tool
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {availableTemplates.map((template) => (
                <DropdownMenuItem
                  key={template.id}
                  onSelect={() => onAddDefault(template)}
                  className="font-mono text-sm"
                >
                  {template.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {defaultTools.length > 0 ? (
        defaultTools.map(({ tool, index }) => (
          <ToolRow
            key={tool.id}
            name={tool.name}
            description={tool.description}
            url={tool.url}
            method={tool.method}
            paramCount={tool.parameters.length}
            isDefault
            onClick={() => onOpenExisting(index)}
          />
        ))
      ) : (
        <div className="px-5 py-6 text-center text-xs text-muted-foreground/50">
          No default tools added yet
        </div>
      )}
    </div>
  );
}
