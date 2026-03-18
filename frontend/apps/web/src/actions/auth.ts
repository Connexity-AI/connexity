'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { LoginService, UsersService } from '@/client/sdk.gen';
import { isSuccessApiResult } from '@/utils/api';
import { AUTH_COOKIE } from '@/constants/auth';
import { ROUTES } from '@/constants/routes';
import { getPublicEnv } from '@/config/process-env';

import type { BodyLoginLoginAccessToken, UserRegister } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

const { LOGIN } = ROUTES;

/**
 * Reuses FastApi types from client. Just forwards, doesn't validate.
 */
export const loginAction = async (
  _prevState: ApiResult,
  formData: FormData
): Promise<ApiResult> => {
  const { NODE_ENV } = getPublicEnv();

  const body = Object.fromEntries(formData) as BodyLoginLoginAccessToken;
  const apiResponse = await LoginService.loginAccessToken({ body });

  const { response: _, ...result } = apiResponse;

  const isSuccess = isSuccessApiResult(result);
  // UI will display backend error
  if (!isSuccess) return result;

  const { access_token, expires } = result.data;
  const isProd = NODE_ENV === 'production';

  // Convert Unix timestamp (seconds) to a JS Date object
  const expiresDate = new Date(Number(expires) * 1000);

  const cookieStore = await cookies();

  cookieStore.set({
    name: AUTH_COOKIE,
    // args
    value: access_token,
    expires: expiresDate,
    // local
    httpOnly: true,
    secure: isProd,
    // host-only for exact frontend domain
    path: '/',
    sameSite: 'lax',
    domain: undefined,
  });

  // success result is ignored, just for type
  return result;
};

export const registerAction = async (
  _prevState: ApiResult,
  formData: FormData
): Promise<ApiResult> => {
  const body = Object.fromEntries(formData) as UserRegister;

  const apiResponse = await UsersService.registerUser({ body });

  const { response: _, ...result } = apiResponse;

  return result;
};

export const logoutAction = async (): Promise<void> => {
  const cookiesList = await cookies();
  cookiesList.delete(AUTH_COOKIE);

  redirect(LOGIN);
};
