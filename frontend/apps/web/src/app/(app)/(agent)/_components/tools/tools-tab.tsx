'use client';

import { Plus } from 'lucide-react';
import { Button } from '@workspace/ui/components/ui/button';
import { TabsContent } from '@workspace/ui/components/ui/tabs';

import { useToolsField } from '@/app/(app)/(agent)/_hooks/use-tools-field';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { ToolEditor } from '@/app/(app)/(agent)/_components/tools/tool-editor';
import { DraftToolEditor } from '@/app/(app)/(agent)/_components/tools/draft/draft-tool-editor';
import { ToolRow } from '@/app/(app)/(agent)/_components/tools/tool-row';
import { ToolsEmptyState } from '@/app/(app)/(agent)/_components/tools/tools-empty-state';

export function ToolsTab() {
  const { isReadOnly } = useAgentEditFormActions();
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
  } = useToolsField();

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

  if (fields.length === 0) {
    return (
      <TabsContent value="tools" className="flex-1 mt-0 flex flex-col min-h-0">
        <ToolsEmptyState onAdd={openNew} />
      </TabsContent>
    );
  }

  return (
    <TabsContent value="tools" className="flex-1 mt-0 flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-border shrink-0">
        <p className="text-xs text-muted-foreground">
          {fields.length} tool{fields.length !== 1 ? 's' : ''}
        </p>
        {!isReadOnly && (
          <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs" onClick={openNew}>
            <Plus className="w-3 h-3" />
            Add tool
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        {fields.map((field, index) => {
          const tool = tools[index];
          return (
            <ToolRow
              key={field.id}
              name={tool?.name ?? ''}
              description={tool?.description ?? ''}
              url={tool?.url ?? ''}
              method={tool?.method ?? 'GET'}
              paramCount={tool?.parameters?.length ?? 0}
              onClick={() => openExisting(index)}
            />
          );
        })}
      </div>
    </TabsContent>
  );
}
