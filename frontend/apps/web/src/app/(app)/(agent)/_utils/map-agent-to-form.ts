/**
 * map-agent-to-form.ts
 *
 * Converts backend API agent data (AgentPublic / AgentVersionPublic) into the
 * shape expected by the agent editor form (AgentFormValues).
 *
 * Why this exists:
 * - The API stores tools using the OpenAI function-calling schema, which is
 *   deeply nested (function -> parameters -> properties, plus platform_config).
 * - The form uses flat, ID'd objects so React Hook Form can manage field arrays
 *   (tools, parameters, auth headers) with stable keys.
 * - Centralizing the mapping here keeps the form context clean and ensures
 *   every hydration path (version, draft, or base agent) is consistent.
 *
 * Used by: agent-edit-form-context.tsx to populate defaultValues when the
 * edit form mounts or when the active version / draft changes.
 */

import { z } from 'zod';
import type { AgentPublic, AgentVersionPublic } from '@/client/types.gen';
import type { AgentFormValues, AgentToolValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { agentFormDefaults } from '@/app/(app)/(agent)/_schemas/agent-form';

// ---------------------------------------------------------------------------
// Zod schema for the incoming OpenAI function-calling tool shape
// ---------------------------------------------------------------------------

/**
 * Describes a single property inside `function.parameters.properties`.
 * We only care about the fields we map to the form; extra keys are stripped.
 */
const propertySchema = z.object({
  description: z.string().optional(),
  type: z.enum(['string', 'number', 'integer']).optional(),
});

/**
 * The `function.parameters` block (JSON Schema subset).
 * `properties` is a record of parameter-name -> schema,
 * `required` lists which of those parameters are mandatory.
 */
const parametersSchema = z.object({
  properties: z.record(z.string(), propertySchema).optional(),
  required: z.array(z.string()).optional(),
});

/** The `function` block inside an OpenAI tool definition. */
const functionSchema = z.object({
  name: z.string().optional(),
  description: z.string().optional(),
  parameters: parametersSchema.optional(),
});

/** Platform-specific implementation details added by our backend. */
const implementationSchema = z.object({
  url: z.string().optional(),
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']).optional(),
  timeout_ms: z.number().optional(),
  headers: z.record(z.string(), z.string()).optional(),
});

const platformConfigSchema = z.object({
  implementation: implementationSchema.optional(),
});

/**
 * Full schema for a single tool as stored by the API.
 * Combines the OpenAI function-calling shape with our platform_config extension.
 * All nested fields are optional — defaults are applied in the mapping function.
 */
const openAIToolSchema = z.object({
  function: functionSchema.optional(),
  platform_config: platformConfigSchema.optional(),
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * The subset of agent fields needed for the mapping.
 * Works with both AgentPublic (latest) and AgentVersionPublic (pinned version).
 */
type VersionableAgent = Pick<
  AgentPublic | AgentVersionPublic,
  'system_prompt' | 'tools' | 'agent_model' | 'agent_provider' | 'agent_temperature'
>;

// ---------------------------------------------------------------------------
// UID helper
// ---------------------------------------------------------------------------

/**
 * Monotonically-incrementing counter combined with Date.now() to produce
 * unique IDs for form field-array rows. React Hook Form needs a stable `id`
 * on each row to track additions / removals without re-rendering siblings.
 */
let counter = 0;
const uid = (prefix: string) => `${prefix}_${Date.now()}_${++counter}`;

// ---------------------------------------------------------------------------
// Mapping functions
// ---------------------------------------------------------------------------

/**
 * Maps a single tool from the OpenAI function-calling schema into the flat
 * form shape used by the agent editor.
 *
 * Uses `openAIToolSchema.parse()` to safely validate the incoming shape.
 * All nested fields are optional in the schema — defaults are applied here
 * via nullish coalescing so the form always receives complete values.
 */
function mapOpenAIToolToForm(rawTool: unknown): AgentToolValues {
  const tool = openAIToolSchema.parse(rawTool);

  const fn = tool.function;
  const params = fn?.parameters;
  const properties = params?.properties ?? {};
  const required = params?.required ?? [];

  const impl = tool.platform_config?.implementation;
  const headers = impl?.headers ?? {};

  // Convert the headers object { key: value } into an array of { id, key, value }
  // so each header gets its own row in the form's field array.
  const authHeaders = Object.entries(headers).map(([key, value]) => ({
    id: uid('auth'),
    key,
    value,
  }));

  // Convert the JSON Schema `properties` object into an array of parameter rows.
  // Cross-references `required` to set the boolean flag per parameter.
  const parameters = Object.entries(properties).map(([name, schema]) => ({
    id: uid('param'),
    name,
    description: schema.description ?? '',
    required: required.includes(name),
    type: (schema.type ?? 'string') as 'string' | 'number' | 'integer',
  }));

  return {
    id: uid('tool'),
    name: fn?.name ?? '',
    description: fn?.description ?? '',
    url: impl?.url ?? '',
    method: impl?.method ?? 'POST',
    // API stores timeout in milliseconds; form displays it in seconds.
    timeout: impl?.timeout_ms ? Math.round(impl.timeout_ms / 1000) : 3,
    authHeaders,
    parameters,
  };
}

/**
 * Converts a backend agent (or agent version / draft) into the form values
 * object consumed by the agent editor's React Hook Form instance.
 *
 * Falls back to `agentFormDefaults` for any missing top-level fields so the
 * form always receives valid, complete defaults.
 */
export function mapAgentToForm(agent: VersionableAgent): AgentFormValues {
  const tools: AgentToolValues[] = (agent.tools ?? []).map((tool) => mapOpenAIToolToForm(tool));

  return {
    prompt: agent.system_prompt ?? '',
    tools,
    provider: agent.agent_provider ?? agentFormDefaults.provider,
    model: agent.agent_model ?? agentFormDefaults.model,
    temperature: agent.agent_temperature ?? agentFormDefaults.temperature,
  };
}
