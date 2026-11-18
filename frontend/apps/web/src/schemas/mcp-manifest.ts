import { z } from 'zod';

/** `GET /manifest` from the MCP server: the contract /mcp-docs shows. The MCP server is
 * not part of the backend's OpenAPI, so its shape is checked here. */
const inputSchema = z.object({
  name: z.string(),
  type: z.string(),
  required: z.boolean(),
  description: z.string().nullable().optional(),
});

const toolSchema = z.object({
  name: z.string(),
  effect: z.enum(['reads', 'writes', 'reads_platform', 'talks_to_agent']),
  needs_yes: z.boolean(),
  only_when_asked: z.boolean(),
  line: z.string(),
  guide: z.string(),
  inputs: z.array(inputSchema),
});

const textSchema = z.object({
  key: z.string(),
  text: z.string(),
  label: z.string().nullable().optional(),
});

export const mcpManifestSchema = z.object({
  version: z.string(),
  server_url: z.string().nullable(),
  tool_count: z.number(),
  guide_count: z.number(),
  effects: z.array(textSchema),
  groups: z.array(
    z.object({
      key: z.string(),
      name: z.string(),
      purpose: z.string(),
      tools: z.array(toolSchema),
    })
  ),
  guides: z.array(
    z.object({ uri: z.string(), name: z.string(), title: z.string(), text: z.string() })
  ),
});

export type McpManifest = z.infer<typeof mcpManifestSchema>;
export type McpManifestTool = z.infer<typeof toolSchema>;
export type McpManifestGuide = McpManifest['guides'][number];

/** `GET /api/v1/onboarding/steps`, checked as the manifest is. */
export const onboardingStepsSchema = z.array(
  z.object({
    key: z.string(),
    title: z.string(),
    who: z.enum(['person', 'assistant']),
    done_when: z.string(),
    instructions: z.array(z.string()),
  })
);
