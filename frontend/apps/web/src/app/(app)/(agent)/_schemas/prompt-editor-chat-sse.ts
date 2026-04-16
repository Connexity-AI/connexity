import { z } from 'zod';

// Runtime-validated SSE payloads. The backend sends these over a text/event-stream
// channel that isn't part of OpenAPI, so we can't rely on Hey API codegen here —
// validate at the stream boundary instead of casting `unknown` and hoping.

export const chatPhaseSchema = z.enum(['idle', 'analyzing', 'editing', 'complete']);
export type ChatPhase = z.infer<typeof chatPhaseSchema>;

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  isStreaming?: boolean;
};

const promptEditorMessageSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  role: z.enum(['user', 'assistant', 'system', 'tool']),
  content: z.string(),
  created_at: z.string(),
});

export const sseEventSchema = z.discriminatedUnion('event', [
  z.object({
    event: z.literal('status'),
    data: z.object({
      phase: chatPhaseSchema,
      message_id: z.string().optional(),
    }),
  }),
  z.object({
    event: z.literal('reasoning'),
    data: z.object({
      content: z.string(),
    }),
  }),
  z.object({
    event: z.literal('edit'),
    data: z.object({
      edited_prompt: z.string(),
      edit_index: z.number(),
      total_edits: z.number(),
    }),
  }),
  z.object({
    event: z.literal('done'),
    data: z.object({
      message: promptEditorMessageSchema,
      edited_prompt: z.string().nullable(),
      base_prompt: z.string(),
    }),
  }),
  z.object({
    event: z.literal('error'),
    data: z.object({
      code: z.string().optional(),
      detail: z.string().optional(),
    }),
  }),
]);

export type SseEvent = z.infer<typeof sseEventSchema>;
