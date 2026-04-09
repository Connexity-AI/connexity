'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import { DraftAuthHeaderRow } from '@/app/(app)/(agent)/_components/draft-auth-header-row';
import { DraftToolEditorHeader } from '@/app/(app)/(agent)/_components/draft-tool-editor-header';
import { DraftToolParameters } from '@/app/(app)/(agent)/_components/draft-tool-parameters';
import {
  Field,
  SectionHeading,
} from '@/app/(app)/(agent)/_components/tool-editor-field';
import { useDraftTool } from '@/app/(app)/(agent)/_hooks/use-draft-tool';

import type {
  AgentToolValues,
  HttpMethod,
} from '@/app/(app)/(agent)/_schemas/agent-form';

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

const METHOD_COLOR: Record<HttpMethod, string> = {
  GET: 'text-green-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-400',
  PATCH: 'text-purple-400',
  DELETE: 'text-red-400',
};

interface DraftToolEditorProps {
  onSave: (tool: AgentToolValues) => void;
  onBack: () => void;
}

export function DraftToolEditor({ onSave, onBack }: DraftToolEditorProps) {
  const {
    draft,
    set,
    setToolName,
    setMethod,
    addAuthHeader,
    removeAuth,
    updateAuthHeader,
    addParameter,
    removeParameter,
    updateParameter,
  } = useDraftTool();

  return (
    <div className="flex flex-col h-full w-full bg-background">
      <DraftToolEditorHeader toolName={draft.name} onBack={onBack} onSave={() => onSave(draft)} />

      <div className="flex-1 overflow-auto">
        <div className="px-8 py-6 space-y-8">
          {/* Identity */}
          <div>
            <SectionHeading>Identity</SectionHeading>
            <div className="space-y-4">
              <Field
                label="Tool name"
                hint="snake_case — the model uses this name to reference the tool"
              >
                <Input
                  value={draft.name}
                  onChange={(e) => setToolName(e.target.value.replace(/\s/g, '_').toLowerCase())}
                  placeholder="e.g. get_available_time"
                  className="h-9 text-sm font-mono"
                />
              </Field>

              <Field
                label="Description"
                hint="The model reads this to decide when to invoke the tool. Be specific about the trigger condition."
              >
                <Textarea
                  value={draft.description}
                  onChange={(e) => set('description', e.target.value)}
                  placeholder="Describe what this tool does and when the model should call it..."
                  className="resize-none text-sm h-24"
                />
              </Field>
            </div>
          </div>

          {/* Endpoint */}
          <div>
            <SectionHeading>Endpoint</SectionHeading>
            <div className="space-y-4">
              <div className="flex gap-3">
                <Field label="Method">
                  <Select value={draft.method} onValueChange={(v) => setMethod(v as HttpMethod)}>
                    <SelectTrigger
                      className={cn('h-9 text-sm font-mono w-[120px]', METHOD_COLOR[draft.method])}
                    >
                      <SelectValue />
                    </SelectTrigger>

                    <SelectContent>
                      {HTTP_METHODS.map((m) => (
                        <SelectItem
                          key={m}
                          value={m}
                          className={cn('font-mono text-sm', METHOD_COLOR[m])}
                        >
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="URL" className="flex-1 min-w-0">
                  <Input
                    value={draft.url}
                    onChange={(e) => set('url', e.target.value)}
                    placeholder="https://api.example.com/endpoint"
                    className="h-9 text-sm font-mono w-full"
                  />
                </Field>
              </div>

              <Field label="Timeout (seconds)">
                <Input
                  type="number"
                  min={1}
                  max={120}
                  value={draft.timeout}
                  onChange={(e) => set('timeout', Math.max(1, parseInt(e.target.value) || 3))}
                  className="h-9 text-sm font-mono w-[120px]"
                />
              </Field>
            </div>
          </div>

          {/* Auth headers */}
          <div>
            <SectionHeading>Auth headers</SectionHeading>
            <div className="space-y-2">
              {draft.authHeaders.length > 0 && (
                <div className="flex items-center gap-2 mb-1 px-0.5">
                  <span className="text-[10px] text-muted-foreground/40 flex-2">Key</span>
                  <span className="text-[10px] text-muted-foreground/40 flex-3">Value</span>
                  <span className="w-8" />
                </div>
              )}
              {draft.authHeaders.map((header, i) => (
                <DraftAuthHeaderRow
                  key={header.id}
                  header={header}
                  onChange={(patch) => updateAuthHeader(i, patch)}
                  onRemove={() => removeAuth(i)}
                />
              ))}
              <Button
                variant="ghost"
                onClick={addAuthHeader}
                className="h-auto p-0 font-normal flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground hover:bg-transparent transition-colors pt-1"
              >
                <Plus className="w-3.5 h-3.5" />
                Add header
              </Button>
            </div>
          </div>

          {/* Parameters */}
          <div>
            <SectionHeading>Parameters</SectionHeading>
            <p className="text-xs text-muted-foreground/50 mb-4 leading-relaxed">
              Define the arguments the model should collect and pass when calling this tool. Each
              parameter becomes a field in the JSON body or query string.
            </p>
            <DraftToolParameters
              parameters={draft.parameters}
              onAdd={addParameter}
              onUpdate={updateParameter}
              onRemove={removeParameter}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
