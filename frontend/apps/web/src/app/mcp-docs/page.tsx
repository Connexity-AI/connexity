import { McpDocsView } from '@/components/mcp-docs/mcp-docs-view';
import { mcpManifestSchema, onboardingStepsSchema } from '@/schemas/mcp-manifest';
import { getPublicEnv } from '@/config/process-env';

import type { OnboardingStepPublic } from '@/client/types.gen';
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

// The onboarding steps, in order, from the backend's public list. Left out when they
// cannot be read; the server log says why.
const readOnboarding = async (): Promise<OnboardingStepPublic[]> => {
  const { API_URL } = getPublicEnv();
  if (!API_URL) {
    console.warn('/mcp-docs could not read the onboarding steps: API_URL is not set');
    return [];
  }
  try {
    const response = await fetch(`${API_URL}/api/v1/onboarding/steps`, { next: { revalidate } });
    if (!response.ok) {
      console.warn(`/mcp-docs could not read the onboarding steps: ${response.status}`);
      return [];
    }
    const parsed = onboardingStepsSchema.safeParse(await response.json());
    if (!parsed.success) {
      console.warn('/mcp-docs could not read the onboarding steps: unexpected shape');
      return [];
    }
    return parsed.data;
  } catch (error) {
    console.warn(
      `/mcp-docs could not read the onboarding steps: ${error instanceof Error ? error.name : 'unknown'}`
    );
    return [];
  }
};

/** The public MCP contract (designs/screens/Connexity MCP Docs.dc.html): no login, not
 * in the sidebar, no workspace data. Built from the MCP server's `GET /manifest`. */
const McpDocsPage = async () => {
  const [manifest, onboarding] = await Promise.all([readManifest(), readOnboarding()]);
  return <McpDocsView manifest={manifest} onboarding={onboarding} />;
};

export default McpDocsPage;
