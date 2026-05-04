import { z } from 'zod';

import { getPredefinedTools } from '@/actions/config';
import { defaultToolTemplateKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

import type { ToolParameterValues } from '@/app/(app)/(agent)/_schemas/agent-form';

export interface DefaultToolTemplate {
  id: string;
  name: string;
  description: string;
  parameters: ToolParameterValues[];
  predefined: boolean;
  terminating: boolean;
}

const propertySchema = z.object({
  description: z.string().optional(),
  type: z.enum(['string', 'number', 'integer']).optional(),
});

const parametersSchema = z.object({
  properties: z.record(z.string(), propertySchema).optional(),
  required: z.array(z.string()).optional(),
});

const functionSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  parameters: parametersSchema.optional(),
});

const platformConfigSchema = z.object({
  predefined: z.boolean().optional(),
  terminating: z.boolean().optional(),
});

const predefinedToolSchema = z.object({
  function: functionSchema,
  platform_config: platformConfigSchema.optional(),
});

let counter = 0;
const uid = (prefix: string) => `${prefix}_${Date.now()}_${++counter}`;

function toTemplate(raw: unknown): DefaultToolTemplate | null {
  const parsed = predefinedToolSchema.safeParse(raw);
  if (!parsed.success) return null;

  const fn = parsed.data.function;
  const properties = fn.parameters?.properties ?? {};
  const required = fn.parameters?.required ?? [];

  const parameters: ToolParameterValues[] = Object.entries(properties).map(
    ([name, schema]) => ({
      id: uid('param'),
      name,
      description: schema.description ?? '',
      required: required.includes(name),
      type: (schema.type ?? 'string') as 'string' | 'number' | 'integer',
    })
  );

  return {
    id: fn.name,
    name: fn.name,
    description: fn.description ?? '',
    parameters,
    predefined: parsed.data.platform_config?.predefined ?? true,
    terminating: parsed.data.platform_config?.terminating ?? false,
  };
}

async function fetchDefaultToolTemplates(): Promise<DefaultToolTemplate[]> {
  const response = await getPredefinedTools();
  if (!isSuccessApiResult(response)) return [];
  return response.data.data
    .map(toTemplate)
    .filter((t): t is DefaultToolTemplate => t !== null);
}

export const defaultToolTemplatesQueries = {
  list: {
    queryKey: defaultToolTemplateKeys.list(),
    queryFn: fetchDefaultToolTemplates,
    staleTime: 5 * 60 * 1000,
  },
};
