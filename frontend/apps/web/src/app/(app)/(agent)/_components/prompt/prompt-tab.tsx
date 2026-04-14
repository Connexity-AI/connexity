'use client';

import { useRef } from 'react';

import { useFormContext } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { TabsContent } from '@workspace/ui/components/ui/tabs';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import { AiSuggestionDiff } from '@/app/(app)/(agent)/_components/diff/ai-suggestion-diff';
import { DiffControls } from '@/app/(app)/(agent)/_components/diff/diff-controls';
import { DiffView } from '@/app/(app)/(agent)/_components/diff/diff-view';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAiSuggestion } from '@/app/(app)/(agent)/_context/ai-suggestion-context';
import { useDiff } from '@/app/(app)/(agent)/_context/diff-context';
import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useAgentDraft } from '@/app/(app)/(agent)/_hooks/use-agent-draft';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';

import type { DiffVersionId } from '@/app/(app)/(agent)/_context/diff-context';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

export function PromptTab() {
  const form = useFormContext<AgentFormValues>();
  const { isReadOnly, agentId } = useAgentEditFormActions();
  const { showDiff, diffFromVersion, diffToVersion, setDiffFromVersion, setDiffToVersion } =
    useDiff();
  const { data: versionsData } = useAgentVersions(agentId);
  const versions = versionsData?.data ?? [];
  const { data: agent } = useAgent(agentId);
  const { data: draft } = useAgentDraft(agentId, agent?.has_draft === true);
  const { suggestedPrompt, clearSuggestion } = useAiSuggestion();
  const diffScrollRef = useRef<HTMLDivElement>(null);

  const resolveContent = (versionId: DiffVersionId): string => {
    if (versionId === 'draft') {
      // When viewing a historical version, react-hook-form is populated with
      // that version's data (see agent-edit-form-context.tsx), so reading the
      // form here would incorrectly return the version's prompt. Read the
      // draft directly from the query instead, falling back to the published
      // agent when no draft exists, and finally to the form (for non-read-only
      // mode where the form is the source of truth for unsaved edits).
      if (draft?.system_prompt !== undefined && draft.system_prompt !== null) {
        return draft.system_prompt;
      }
      if (agent?.system_prompt !== undefined && agent.system_prompt !== null) {
        return agent.system_prompt;
      }
      return form.getValues().prompt ?? '';
    }

    const match = versions.find((version) => version.version === versionId);
    return match?.system_prompt ?? '';
  };

  const diffMode = showDiff && isReadOnly;

  // AI suggestion diff takes precedence over the plain textarea. The version-
  // diff branch above still wins because it requires `isReadOnly`, and we
  // never show AI diff in read-only mode (autosave is disabled there).
  if (suggestedPrompt !== null && !isReadOnly) {
    const diffBase = form.getValues().prompt ?? '';

    const handleAccept = () => {
      form.setValue('prompt', suggestedPrompt, {
        shouldDirty: true,
        shouldTouch: true,
      });
      clearSuggestion();
    };

    const handleDecline = () => {
      clearSuggestion();
    };

    return (
      <TabsContent value="prompt" className="flex-1 mt-0 p-6 flex flex-col min-h-0">
        <AiSuggestionDiff
          draftContent={diffBase}
          suggestedContent={suggestedPrompt}
          isBusy={false}
          onAccept={handleAccept}
          onDecline={handleDecline}
        />
      </TabsContent>
    );
  }

  if (diffMode) {
    return (
      <TabsContent value="prompt" className="flex-1 mt-0 min-h-0 overflow-hidden relative">
        {/*
          Absolute-positioned scroll container. We use `absolute inset-0`
          (rather than `flex-1 min-h-0`) because the Tabs/main parent chain
          mixes flex-1 and h-full in ways that don't always resolve to a
          fixed height — which caused the inner div to grow with its content
          and the page body to scroll instead, leaving the sticky bar with
          no actual scrolling ancestor. Pinning this div to the padding box
          of TabsContent guarantees it has a bounded height, that overflow
          happens inside it, and that `position: sticky` inside it works.
        */}
        <div ref={diffScrollRef} className="absolute inset-0 overflow-y-auto px-6 pb-6">
          {/*
            24px spacer above the diff bar. We deliberately *don't* use
            `pt-6` on the scroll container: that would leave a 24px gap
            between the stuck bar and the tabs above, because sticky `top-0`
            positions the element at the scrollport top — which sits below
            the container's top padding. Using an in-flow spacer instead
            means the gap exists at rest, scrolls away with the content,
            and lets the sticky bar pin flush against the scroll container
            edge (right under the tab selectors).
          */}
          <div aria-hidden className="h-6 shrink-0" />
          <DiffControls
            versions={versions}
            fromVersion={diffFromVersion}
            toVersion={diffToVersion}
            onFromChange={setDiffFromVersion}
            onToChange={setDiffToVersion}
            scrollRootRef={diffScrollRef}
          />
          <DiffView
            fromContent={resolveContent(diffFromVersion)}
            toContent={resolveContent(diffToVersion)}
          />
        </div>
      </TabsContent>
    );
  }

  return (
    <TabsContent value="prompt" className="flex-1 mt-0 p-6 flex flex-col min-h-0">
      <FormField
        control={form.control}
        name="prompt"
        render={({ field }) => (
          <FormItem className="flex-1 flex flex-col min-h-0">
            <FormControl>
              <Textarea
                {...field}
                placeholder="Enter your prompt here..."
                className="w-full flex-1 resize-none min-h-0"
                readOnly={isReadOnly}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </TabsContent>
  );
}
