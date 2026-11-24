import { NoWorkspaces } from '@/components/shell/no-workspaces';
import { WorkspacesService } from '@/client/sdk.gen';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

/**
 * The pages that show one workspace: Work, Dashboard, Agents, Calls and Issues. A
 * person whose agency has no workspace has none to show, and sees how to create one.
 * Agency settings and Account sit outside this group and stay reachable.
 *
 * The empty state shows only when the list was read and is empty. A read that failed
 * is an error like any other, never an invitation to create a workspace.
 */
const WorkspaceLayout: FC<Props> = async ({ children }) => {
  const { data: workspaces } = await WorkspacesService.listWorkspaces();
  if (!workspaces) throw new Error('The workspaces could not be loaded.');
  if (workspaces.length === 0) return <NoWorkspaces />;
  return children;
};

export default WorkspaceLayout;
