import { z } from 'zod';

import {
  BOOTSTRAP_DEFAULT_LLM_ROUTE,
  splitDefaultLlmRouting,
} from '@/utils/split-default-llm-routing';

const _bootstrapForm = splitDefaultLlmRouting(BOOTSTRAP_DEFAULT_LLM_ROUTE);

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

const agentToolSchema = z
  .object({
    id: z.string(),
    name: z.string().min(1, 'Tool name is required'),
    description: z.string(),
    url: z.string(),
    method: z.enum(HTTP_METHODS),
    timeout: z.number().min(1).max(120),
    authHeaders: z.array(authHeaderSchema),
    parameters: z.array(toolParameterSchema),
    isDefault: z.boolean().optional(),
  })
  .superRefine((tool, ctx) => {
    const counts = new Map<string, number>();
    for (const p of tool.parameters) {
      if (p.name) counts.set(p.name, (counts.get(p.name) ?? 0) + 1);
    }
    tool.parameters.forEach((p, i) => {
      if (p.name && (counts.get(p.name) ?? 0) > 1) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['parameters', i, 'name'],
          message: 'Duplicate parameter name',
        });
      }
    });
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
  provider: _bootstrapForm.provider,
  model: _bootstrapForm.model,
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
    method: 'POST',
    timeout: 3,
    authHeaders: [],
    parameters: [],
    ...overrides,
  };
}

export function makeDefaultToolFromTemplate(template: {
  name: string;
  description: string;
}): AgentToolValues {
  return {
    id: uid('tool'),
    name: template.name,
    description: template.description,
    url: '',
    method: 'POST',
    timeout: 3,
    authHeaders: [],
    parameters: [],
    isDefault: true,
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

// ─── Validation helpers (for draft tool editor — outside react-hook-form) ────

export function validateParameterName(name: string, allNames: string[]): string | undefined {
  if (!name) return 'Parameter name is required';
  const occurrences = allNames.reduce((n, current) => (current === name ? n + 1 : n), 0);
  if (occurrences > 1) return 'Duplicate parameter name';
  return undefined;
}
