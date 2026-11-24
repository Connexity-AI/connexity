'use server';

import { listWorkspaces, openWorkspaceAction } from '@/actions/workspaces';
import { AgenciesService } from '@/client/sdk.gen';
import { getApiErrorMessage } from '@/utils/error';

import type {
  AgencyInviteCreate,
  AgencyInviteResult,
  AgencyMemberUpdate,
  DeletionState,
  WorkspaceDeletionPreview,
} from '@/client/types.gen';

export type AgencyActionResult = { ok: true } | { ok: false; message: string };

const failed = (error: unknown): AgencyActionResult => ({
  ok: false,
  message: getApiErrorMessage(error),
});

/** Invite people; the answer says who was invited and who was not, with why. */
export const invitePeopleAction = async (
  agencyId: string,
  body: AgencyInviteCreate
): Promise<{ ok: true; result: AgencyInviteResult } | { ok: false; message: string }> => {
  const { data, error } = await AgenciesService.invitePeople({
    path: { agency_id: agencyId },
    body,
  });
  if (!data) return { ok: false, message: getApiErrorMessage(error) };
  return { ok: true, result: data };
};

export const resendInviteAction = async (
  agencyId: string,
  inviteId: string
): Promise<AgencyActionResult> => {
  const { data, error } = await AgenciesService.resendInvite({
    path: { agency_id: agencyId, invite_id: inviteId },
  });
  return data ? { ok: true } : failed(error);
};

export const cancelInviteAction = async (
  agencyId: string,
  inviteId: string
): Promise<AgencyActionResult> => {
  const { response, error } = await AgenciesService.cancelInvite({
    path: { agency_id: agencyId, invite_id: inviteId },
  });
  return response?.status === 204 ? { ok: true } : failed(error);
};

export const updateMemberAction = async (
  agencyId: string,
  userId: string,
  body: AgencyMemberUpdate
): Promise<AgencyActionResult> => {
  const { data, error } = await AgenciesService.updateMember({
    path: { agency_id: agencyId, user_id: userId },
    body,
  });
  return data ? { ok: true } : failed(error);
};

export const removeMemberAction = async (
  agencyId: string,
  userId: string
): Promise<AgencyActionResult> => {
  const { response, error } = await AgenciesService.removeMember({
    path: { agency_id: agencyId, user_id: userId },
  });
  return response?.status === 204 ? { ok: true } : failed(error);
};

/** What deleting a workspace would remove, for the dialog that confirms it. */
export const previewDeletionAction = async (
  agencyId: string,
  workspaceId: string
): Promise<{ ok: true; preview: WorkspaceDeletionPreview } | { ok: false; message: string }> => {
  const { data, error } = await AgenciesService.previewDeletion({
    path: { agency_id: agencyId, workspace_id: workspaceId },
  });
  if (!data) return { ok: false, message: getApiErrorMessage(error) };
  return { ok: true, preview: data };
};

/**
 * After a deletion, give the person who deleted a session in the workspace they have
 * open now. Without it, a person who deleted the workspace they were in would be shown
 * the page meant for everyone else who had it open.
 */
const moveSession = async (): Promise<void> => {
  const open = (await listWorkspaces()).find((w) => w.is_open);
  if (open) await openWorkspaceAction(open.id);
};

type DeletionResult = { ok: true; state: DeletionState } | { ok: false; message: string };

/** Delete a workspace for good. `name` is what the person typed to confirm. */
export const deleteWorkspaceAction = async (
  agencyId: string,
  workspaceId: string,
  name: string
): Promise<DeletionResult> => {
  const { data, error } = await AgenciesService.deleteWorkspace({
    path: { agency_id: agencyId, workspace_id: workspaceId },
    body: { name },
  });
  if (!data) return { ok: false, message: getApiErrorMessage(error) };
  await moveSession();
  return { ok: true, state: data.state };
};

/** Continue a deletion that failed. */
export const retryDeletionAction = async (
  agencyId: string,
  workspaceId: string
): Promise<DeletionResult> => {
  const { data, error } = await AgenciesService.retryDeletion({
    path: { agency_id: agencyId, workspace_id: workspaceId },
  });
  if (!data) return { ok: false, message: getApiErrorMessage(error) };
  return { ok: true, state: data.state };
};
