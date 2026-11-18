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

// Why the page could not read the contract, in the server log; never the answer itself.
const unreadable = (reason: string): null => {
  console.warn(`/mcp-docs could not read the MCP manifest: ${reason}`);
  return null;
};

const readManifest = async (): Promise<McpManifest | null> => {
  const { MCP_URL } = getPublicEnv();
  if (!MCP_URL) return unreadable('MCP_URL is not set');
  let response: Response;
  try {
    response = await fetch(`${MCP_URL}/manifest`, { next: { revalidate } });
  } catch (error) {
    return unreadable(`request failed (${error instanceof Error ? error.name : 'unknown'})`);
  }
  if (!response.ok) return unreadable(`the MCP server answered ${response.status}`);
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return unreadable('the answer was not JSON');
  }
  const parsed = mcpManifestSchema.safeParse(body);
  if (!parsed.success) {
    const fields = parsed.error.issues.map((issue) => issue.path.join('.') || '(root)');
    return unreadable(`unexpected shape at ${[...new Set(fields)].slice(0, 5).join(', ')}`);
  }
  return parsed.data;
};

/** The public MCP contract (designs/screens/Connexity MCP Docs.dc.html): no login, not
 * in the sidebar, no workspace data. Built from the MCP server's `GET /manifest`. */
const McpDocsPage = async () => {
  const manifest = await readManifest();
  return <McpDocsView manifest={manifest} />;
};

export default McpDocsPage;
