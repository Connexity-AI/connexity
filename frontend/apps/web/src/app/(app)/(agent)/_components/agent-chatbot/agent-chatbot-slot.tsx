'use client';

import { cn } from '@workspace/ui/lib/utils';

import { AgentChatbot } from '@/app/(app)/(agent)/_components/agent-chatbot/agent-chatbot';
import { isConversationFlowAgent } from '@/app/(app)/(agent)/_constants/agent';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';

/**
 * Collapses the chat panel when:
 *  - viewing a historical version (read-only) — autosave is disabled, so an
 *    accepted suggestion would have nowhere to go; or
 *  - the agent is a Retell conversation flow — there is no single prompt for
 *    the assistant to rewrite.
 * Width is animated so the transition feels smooth instead of snapping.
 */
export function AgentChatbotSlot() {
  const { isReadOnly, agent } = useAgentEditFormActions();
  const hidden = isReadOnly || isConversationFlowAgent(agent);

  return (
    <div
      aria-hidden={hidden}
      className={cn(
        'shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out',
        hidden ? 'w-0' : 'w-1/3'
      )}
    >
      <aside className="w-full h-full border-r border-border flex flex-col min-h-0 min-w-0">
        <AgentChatbot />
      </aside>
    </div>
  );
}
