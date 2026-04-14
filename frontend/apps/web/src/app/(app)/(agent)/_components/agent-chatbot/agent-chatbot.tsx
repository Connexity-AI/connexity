'use client';

import { Button } from '@workspace/ui/components/ui/button';

import { useAgentChatbot } from '@/app/(app)/(agent)/_hooks/use-agent-chatbot';
import { ChatInput } from './chat-input';
import { ChatMessagesArea } from './chat-messages-area';

export function AgentChatbot() {
  const {
    sessionError,
    isSessionLoading,
    model,
    setModel,
    messages,
    phase,
    isStreaming,
    streamError,
    sendMessage,
    isHistoryLoading,
    suggestion,
    createNewSession,
    isCreatingSession,
  } = useAgentChatbot();

  return (
    <div className="flex flex-col h-full bg-background">
      <div className="border-b border-border h-11.25 px-4 flex items-center justify-between shrink-0">
        <h2 className="text-sm text-foreground">Agent Assistant</h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => void createNewSession()}
          disabled={isCreatingSession || isStreaming}
          className="h-7 px-2 text-xs"
        >
          + New
        </Button>
      </div>

      <ChatMessagesArea
        sessionError={sessionError}
        isSessionLoading={isSessionLoading}
        messages={messages}
        phase={phase}
        isHistoryLoading={isHistoryLoading}
      />

      {streamError && (
        <div className="px-4 py-2 text-xs text-destructive border-t border-destructive/20 bg-destructive/5 shrink-0">
          {streamError}
        </div>
      )}

      <ChatInput
        onSend={sendMessage}
        disabled={isStreaming || isCreatingSession}
        model={model}
        onModelChange={setModel}
        suggestion={suggestion}
      />
    </div>
  );
}
