'use server';

import { AgenciesService } from '@/client/sdk.gen';
import { getApiErrorMessage } from '@/utils/error';

import type {
  AgencyInviteCreate,
  AgencyInviteResult,
  AgencyMemberUpdate,
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
