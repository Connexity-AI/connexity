import { z } from 'zod';

// ─── Sub-schemas ─────────────────────────────────────────────────────────────

const authHeaderSchema = z.object({
  id: z.string(),
  key: z.string(),
  value: z.string(),
});

const toolParameterSchema = z.object({
  id: z.string(),
  name: z.string().min(1, 'Parameter name is required'),
  description: z.string(),
  required: z.boolean(),
  type: z.enum(['string', 'number', 'integer']),
});

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as const;

const agentToolSchema = z.object({
  id: z.string(),
  name: z.string().min(1, 'Tool name is required'),
  description: z.string(),
  url: z.string(),
  method: z.enum(HTTP_METHODS),
  timeout: z.number().min(1).max(120),
  authHeaders: z.array(authHeaderSchema),
  parameters: z.array(toolParameterSchema),
});

// ─── Main form schema ────────────────────────────────────────────────────────

export const agentFormSchema = z.object({
  prompt: z.string().min(1, 'Prompt is required'),
  tools: z.array(agentToolSchema),
  provider: z.string().min(1),
  model: z.string().min(1),
  temperature: z.number().min(0).max(2),
});

export type AgentFormValues = z.infer<typeof agentFormSchema>;
export type AgentToolValues = z.infer<typeof agentToolSchema>;
export type ToolParameterValues = z.infer<typeof toolParameterSchema>;
export type AuthHeaderValues = z.infer<typeof authHeaderSchema>;
export type HttpMethod = (typeof HTTP_METHODS)[number];

// ─── Default values ──────────────────────────────────────────────────────────

export const agentFormDefaults: AgentFormValues = {
  prompt: '',
  tools: [],
  provider: 'OpenAI',
  model: 'gpt-4.1',
  temperature: 0.7,
};

// ─── Factory functions (for useFieldArray.append) ────────────────────────────

let counter = 0;
const uid = (prefix: string) => `${prefix}_${Date.now()}_${++counter}`;

export function makeDefaultTool(overrides?: Partial<AgentToolValues>): AgentToolValues {
  return {
    id: uid('tool'),
    name: '',
    description: '',
    url: '',
    method: 'GET',
    timeout: 3,
    authHeaders: [],
    parameters: [],
    ...overrides,
  };
}

export function makeDefaultParam(overrides?: Partial<ToolParameterValues>): ToolParameterValues {
  return {
    id: uid('param'),
    name: '',
    description: '',
    required: false,
    type: 'string',
    ...overrides,
  };
}

export function makeDefaultAuthHeader(overrides?: Partial<AuthHeaderValues>): AuthHeaderValues {
  return {
    id: uid('auth'),
    key: '',
    value: '',
    ...overrides,
  };
}
