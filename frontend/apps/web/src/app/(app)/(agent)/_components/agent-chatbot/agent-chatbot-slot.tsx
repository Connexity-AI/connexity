'use client';

import { cn } from '@workspace/ui/lib/utils';

import { AgentChatbot } from '@/app/(app)/(agent)/_components/agent-chatbot/agent-chatbot';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';

/**
 * Collapses the chat panel when viewing a historical version — in read-only
 * mode autosave is disabled, so any accepted suggestion would have nowhere to
 * go. Width is animated so the transition feels smooth instead of snapping.
 */
export function AgentChatbotSlot() {
  const { isReadOnly } = useAgentEditFormActions();

  return (
    <div
      aria-hidden={isReadOnly}
      className={cn(
        'shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out',
        isReadOnly ? 'w-0' : 'w-1/3'
      )}
    >
      <aside className="w-full h-full border-r border-border flex flex-col min-h-0 min-w-0">
        <AgentChatbot />
      </aside>
    </div>
  );
}
