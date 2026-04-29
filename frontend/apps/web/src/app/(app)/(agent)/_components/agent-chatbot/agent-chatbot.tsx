'use client';

import { useState } from 'react';

import { Button } from '@workspace/ui/components/ui/button';

import { useSuggestFixes } from '@/app/(app)/(agent)/_context/suggest-fixes-context';
import { useAgentChatbot } from '@/app/(app)/(agent)/_hooks/use-agent-chatbot';
import { ChatInput } from './chat-input';
import { ChatMessagesArea } from './chat-messages-area';
import { GuidelinesDialog } from './guidelines-dialog';
import { SuggestFixesAttachments } from './suggest-fixes-attachments';

export function AgentChatbot() {
  const {
    agentId,
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

  const { attachment: suggestFixesAttachment } = useSuggestFixes();
  const hasAttachments = !!suggestFixesAttachment && suggestFixesAttachment.caseSummaries.length > 0;

  const [guidelinesOpen, setGuidelinesOpen] = useState(false);

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
          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
        >
          New Chat
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

      <SuggestFixesAttachments />

      <ChatInput
        onSend={sendMessage}
        disabled={isStreaming || isCreatingSession}
        model={model}
        onModelChange={setModel}
        suggestion={suggestion}
        onOpenGuidelines={() => setGuidelinesOpen(true)}
        allowEmptySend={hasAttachments}
      />

      <GuidelinesDialog agentId={agentId} open={guidelinesOpen} onOpenChange={setGuidelinesOpen} />
    </div>
  );
}
