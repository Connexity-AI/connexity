import { McpDocsView } from '@/components/mcp-docs/mcp-docs-view';
import { mcpManifestSchema } from '@/schemas/mcp-manifest';
import { getPublicEnv } from '@/config/process-env';

import type { McpManifest } from '@/schemas/mcp-manifest';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Connexity MCP',
  description: 'What your assistant can do in Connexity: every tool, what it may do, its inputs.',
};

// Read again every few minutes: the page follows the live MCP server.
export const revalidate = 300;

const readManifest = async (): Promise<McpManifest | null> => {
  const { MCP_URL } = getPublicEnv();
  if (!MCP_URL) return null;
  try {
    const response = await fetch(`${MCP_URL}/manifest`, { next: { revalidate } });
    if (!response.ok) return null;
    const parsed = mcpManifestSchema.safeParse(await response.json());
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
};

/** The public MCP contract (designs/screens/Connexity MCP Docs.dc.html): no login, not
 * in the sidebar, no workspace data. Built from the MCP server's `GET /manifest`. */
const McpDocsPage = async () => {
  const manifest = await readManifest();
  return <McpDocsView manifest={manifest} />;
};

export default McpDocsPage;
