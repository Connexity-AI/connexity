'use client';

import { Plus, Wrench } from 'lucide-react';
import { Button } from '@workspace/ui/components/ui/button';
import { TabsContent } from '@workspace/ui/components/ui/tabs';

import { useToolsField } from '@/app/(app)/(agent)/_hooks/use-tools-field';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { DefaultToolsSection } from '@/app/(app)/(agent)/_components/tools/default-tools-section';
import { ToolEditor } from '@/app/(app)/(agent)/_components/tools/tool-editor';
import { DraftToolEditor } from '@/app/(app)/(agent)/_components/tools/draft/draft-tool-editor';
import { ToolRow } from '@/app/(app)/(agent)/_components/tools/tool-row';
import { ToolsTabSkeleton } from '@/app/(app)/(agent)/_components/tools/tools-tab-skeleton';

import type { AgentToolValues } from '@/app/(app)/(agent)/_schemas/agent-form';

export function ToolsTab() {
  const { isReadOnly, isLoading } = useAgentEditFormActions();
  const {
    fields,
    tools,
    editingIndex,
    isCreating,
    openNew,
    openExisting,
    handleBack,
    handleDelete,
    handleSaveNew,
    addDefaultTool,
  } = useToolsField();

  if (isLoading) return <ToolsTabSkeleton />;

  // Draft editor for new tools (not yet in form state)
  if (isCreating && !isReadOnly) {
    return (
      <TabsContent value="tools" className="flex-1 mt-0 flex flex-col min-h-0">
        <DraftToolEditor onSave={handleSaveNew} onBack={handleBack} />
      </TabsContent>
    );
  }

  // Editor for existing tools (in-place via field array)
  if (editingIndex !== null) {
    return (
      <TabsContent value="tools" className="flex-1 mt-0 flex flex-col min-h-0">
        <ToolEditor
          toolIndex={editingIndex}
          isNew={false}
          onBack={handleBack}
          onDelete={handleDelete}
          readOnly={isReadOnly}
        />
      </TabsContent>
    );
  }

  type IndexedTool = {
    field: (typeof fields)[number];
    tool: AgentToolValues;
    index: number;
  };
  const indexedTools: IndexedTool[] = fields.flatMap((field, index) => {
    const tool = tools[index];
    return tool ? [{ field, tool, index }] : [];
  });
  const defaultTools = indexedTools
    .filter((entry) => entry.tool.isDefault)
    .map((entry) => ({ tool: entry.tool, index: entry.index }));
  const customTools = indexedTools.filter((entry) => !entry.tool.isDefault);

  return (
    <TabsContent value="tools" className="flex-1 mt-0 flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-border shrink-0">
        <p className="text-xs text-muted-foreground">
          {fields.length} tool{fields.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        <DefaultToolsSection
          defaultTools={defaultTools}
          isReadOnly={isReadOnly}
          onAddDefault={addDefaultTool}
          onOpenExisting={openExisting}
        />

        <div>
          <div className="flex items-center justify-between px-5 py-3 bg-accent/5">
            <div className="flex items-center gap-2">
              <Wrench className="w-3.5 h-3.5 text-muted-foreground/60" />
              <span className="text-xs text-muted-foreground uppercase tracking-wider">
                Custom Tools
              </span>
            </div>
            {!isReadOnly && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 h-7 text-xs"
                onClick={openNew}
              >
                <Plus className="w-3 h-3" />
                Add tool
              </Button>
            )}
          </div>

          {customTools.length > 0 ? (
            customTools.map(({ field, tool, index }) => (
              <ToolRow
                key={field.id}
                name={tool.name}
                description={tool.description}
                url={tool.url}
                method={tool.method}
                paramCount={tool.parameters.length}
                onClick={() => openExisting(index)}
              />
            ))
          ) : (
            <div className="px-5 py-6 text-center text-xs text-muted-foreground/50">
              No custom tools added yet
            </div>
          )}
        </div>
      </div>
    </TabsContent>
  );
}
