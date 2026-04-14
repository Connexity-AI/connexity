'use client';

import { ChatMessages } from '@/app/(app)/(agent)/_components/agent-chatbot/chat-messages';

import type { ChatMessage, ChatPhase } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-chat';

interface ChatMessagesAreaProps {
  sessionError: unknown;
  isSessionLoading: boolean;
  messages: ChatMessage[];
  phase: ChatPhase;
  isHistoryLoading: boolean;
}

export function ChatMessagesArea({
  sessionError,
  isSessionLoading,
  messages,
  phase,
  isHistoryLoading,
}: ChatMessagesAreaProps) {
  if (sessionError) {
    return <ChatSessionError error={sessionError} />;
  }

  if (isSessionLoading) {
    return <ChatSessionLoading />;
  }

  return <ChatMessages messages={messages} phase={phase} isHistoryLoading={isHistoryLoading} />;
}

function ChatSessionError({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);

  return (
    <div className="flex-1 flex items-center justify-center p-6 text-xs text-destructive text-center">
      Failed to open chat session: {message}
    </div>
  );
}

function ChatSessionLoading() {
  return (
    <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
      Loading…
    </div>
  );
}
