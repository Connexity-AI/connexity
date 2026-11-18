import { z } from 'zod';

/** `GET /manifest` from the MCP server: the contract /mcp-docs shows. The MCP server is
 * not part of the backend's OpenAPI, so its shape is checked here.
 *
 * The services deploy separately, so for a few minutes this page may read a manifest
 * from an older or newer MCP server. Only what the page cannot draw without is
 * required; everything else falls back (`.catch`), and extra fields are ignored. A
 * manifest field added or removed must never take the page down. */

const EFFECTS = ['reads', 'writes', 'reads_platform', 'talks_to_agent'] as const;

const inputSchema = z.object({
  name: z.string(),
  type: z.string().catch('unknown'),
  required: z.boolean().catch(false),
  description: z.string().nullable().optional().catch(null),
});

const toolSchema = z.object({
  name: z.string(),
  line: z.string(),
  effect: z.enum(EFFECTS).catch('writes'),
  needs_yes: z.boolean().catch(false),
  only_when_asked: z.boolean().catch(false),
  guide: z.string().catch(''),
  inputs: z.array(inputSchema).catch([]),
});

const textSchema = z.object({
  key: z.string(),
  text: z.string().catch(''),
  label: z.string().nullable().optional().catch(null),
});

const guideSchema = z.object({
  uri: z.string(),
  name: z.string().catch(''),
  title: z.string().catch(''),
  text: z.string().catch(''),
});

export const mcpManifestSchema = z
  .object({
    version: z.string().catch('unknown'),
    server_url: z.string().nullable().catch(null),
    tool_count: z.number().optional().catch(undefined),
    guide_count: z.number().optional().catch(undefined),
    effects: z.array(textSchema).catch([]),
    groups: z.array(
      z.object({
        key: z.string(),
        name: z.string(),
        purpose: z.string().catch(''),
        tools: z.array(toolSchema),
      })
    ),
    guides: z.array(guideSchema).catch([]),
  })
  .transform((manifest) => ({
    ...manifest,
    // Worked out from what arrived when the server does not say.
    tool_count:
      manifest.tool_count ?? manifest.groups.reduce((n, group) => n + group.tools.length, 0),
    guide_count: manifest.guide_count ?? manifest.guides.length,
  }));

export type McpManifest = z.infer<typeof mcpManifestSchema>;
export type McpManifestTool = z.infer<typeof toolSchema>;
export type McpManifestGuide = McpManifest['guides'][number];

const stepSchema = z.object({
  key: z.string(),
  title: z.string(),
  who: z.enum(['person', 'assistant']).catch('assistant'),
  done_when: z.string().catch(''),
  instructions: z.array(z.string()).catch([]),
});

/** `GET /api/v1/onboarding/steps`. A step the page cannot show (no key or title) is
 * dropped; the rest fall back as the manifest does. */
export const onboardingStepsSchema = z.array(z.unknown()).transform((steps) =>
  steps.flatMap((step) => {
    const parsed = stepSchema.safeParse(step);
    return parsed.success ? [parsed.data] : [];
  })
);
