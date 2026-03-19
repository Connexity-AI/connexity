'use server';

import { revalidatePath } from 'next/cache';

import { UsersService } from '@/client/sdk.gen';
import { ROUTES } from '@/constants/routes';

import type { UpdatePassword, UserUpdateMe } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

const { SETTINGS } = ROUTES;

export const profileUpdateAction = async (
  _prevState: ApiResult,
  formData: FormData
): Promise<ApiResult> => {
  const body = Object.fromEntries(formData) as UserUpdateMe;

  const apiResponse = await UsersService.updateUserMe({
    body,
  });

  const { response: _, ...result } = apiResponse;

  revalidatePath(SETTINGS);

  return result;
};

/** Can update only his own password. userId not needed. */
export const profilePasswordUpdateAction = async (
  _prevState: ApiResult,
  formData: FormData
): Promise<ApiResult> => {
  const body = Object.fromEntries(formData) as UpdatePassword;

  const apiResponse = await UsersService.updatePasswordMe({ body });

  const { response: _, ...result } = apiResponse;

  revalidatePath(SETTINGS);

  return result;
};

export const profileDeleteAction = async (): Promise<ApiResult> => {
  const apiResponse = await UsersService.deleteUserMe();

  const { response: _, ...result } = apiResponse;

  return result;
};
