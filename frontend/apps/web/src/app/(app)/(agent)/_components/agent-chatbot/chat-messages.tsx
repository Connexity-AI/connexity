'use client';

import { useEffect, useRef } from 'react';

import { ScrollArea } from '@workspace/ui/components/ui/scroll-area';
import { cn } from '@workspace/ui/lib/utils';

import type { ChatMessage, ChatPhase } from '@/app/(app)/(agent)/_hooks/use-prompt-editor-chat';

interface ChatMessagesProps {
  messages: ChatMessage[];
  phase: ChatPhase;
  isHistoryLoading: boolean;
}

export function ChatMessages({ messages, phase, isHistoryLoading }: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, phase]);

  const visibleMessages = messages.filter((message) => message.content.length > 0);
  const hasStreamingContent = messages.some(
    (message) => message.isStreaming && message.content.length > 0
  );
  const isStreaming = phase === 'analyzing' || phase === 'editing';
  const showThinking = isStreaming && !hasStreamingContent;
  const showEmpty = !isHistoryLoading && visibleMessages.length === 0 && !showThinking;

  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-4 p-6">
        {showEmpty && (
          <div className="flex flex-col items-center justify-center text-center text-xs text-muted-foreground py-12 px-4">
            <p className="mb-1">Ask the assistant to improve your prompt.</p>
            <p className="text-muted-foreground/60">
              Try: &ldquo;Review this prompt and suggest improvements.&rdquo;
            </p>
          </div>
        )}

        {visibleMessages.map((message) => (
          <div
            key={message.id}
            className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            <div
              className={cn(
                'max-w-[82%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-line wrap-break-word',
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-muted text-foreground rounded-bl-sm'
              )}
            >
              {message.content}
            </div>
          </div>
        ))}

        {showThinking && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
              <Dot delay="0ms" />
              <Dot delay="150ms" />
              <Dot delay="300ms" />
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50 animate-bounce"
      style={{ animationDelay: delay }}
    />
  );
}
