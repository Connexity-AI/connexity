'use server';

import { setSessionCookie } from '@/actions/auth';
import { WorkspacesService } from '@/client/sdk.gen';
import { isSuccessApiResult } from '@/utils/api';

import type { WorkspacePublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const listWorkspaces = async (): Promise<WorkspacePublic[]> => {
  const result = await WorkspacesService.listWorkspaces();
  return result.data ?? [];
};

/** Make a workspace the open one, and swap the session cookie to match. */
export const openWorkspaceAction = async (workspaceId: string): Promise<ApiResult> => {
  const apiResponse = await WorkspacesService.openWorkspace({
    path: { workspace_id: workspaceId },
  });
  const { response: _, ...result } = apiResponse;

  if (isSuccessApiResult(result))
    await setSessionCookie(result.data.access_token, result.data.expires);
  return result;
};

/** Create a workspace and open it, as the New workspace dialog does. */
export const createWorkspaceAction = async (name: string): Promise<ApiResult> => {
  const apiResponse = await WorkspacesService.createWorkspace({ body: { name } });
  const { response: _, ...result } = apiResponse;

  if (!isSuccessApiResult(result)) return result;
  return openWorkspaceAction(result.data.id);
};
