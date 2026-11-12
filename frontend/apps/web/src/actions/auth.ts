'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { LoginService, UsersService } from '@/client/sdk.gen';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { AUTH_COOKIE } from '@/constants/auth';
import { getPublicEnv } from '@/config/process-env';

import type { BodyLoginLoginAccessToken } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

/** Set the session token from the backend as the HttpOnly auth cookie. */
export const setSessionCookie = async (accessToken: string, expires: number): Promise<void> => {
  const { NODE_ENV } = getPublicEnv();
  const cookieStore = await cookies();

  cookieStore.set({
    name: AUTH_COOKIE,
    value: accessToken,
    expires: new Date(Number(expires) * 1000),
    httpOnly: true,
    secure: NODE_ENV === 'production',
    path: '/',
    sameSite: 'lax',
    domain: undefined,
  });
};

export const loginAction = async (body: BodyLoginLoginAccessToken): Promise<ApiResult> => {
  const apiResponse = await LoginService.loginAccessToken({ body });
  const { response: _, ...result } = apiResponse;

  if (!isSuccessApiResult(result)) return result;

  await setSessionCookie(result.data.access_token, result.data.expires);
  return result;
};

export interface SignUpValues {
  full_name: string;
  email: string;
  password: string;
}

export type SignUpResult =
  | { ok: true }
  | { ok: false; reason: 'emailTaken' | 'shortPassword' | 'other'; message: string };

const EMAIL_TAKEN = 'The user with this email already exists in the system';

/** Create the account, then sign in, so the app opens straight away. */
export const signUpAction = async (values: SignUpValues): Promise<SignUpResult> => {
  const registered = await UsersService.registerUser({
    body: {
      email: values.email,
      password: values.password,
      full_name: values.full_name || null,
    },
  });

  if (registered.error !== undefined) {
    const message = getApiErrorMessage(registered.error);
    if (message === EMAIL_TAKEN) return { ok: false, reason: 'emailTaken', message };
    if (registered.response.status === 422 && values.password.length < 8)
      return { ok: false, reason: 'shortPassword', message };
    if (registered.response.status === 422)
      return { ok: false, reason: 'other', message: 'Enter a valid email address.' };
    return { ok: false, reason: 'other', message };
  }

  const signedIn = await loginAction({ username: values.email, password: values.password });
  if (isErrorApiResult(signedIn))
    return { ok: false, reason: 'other', message: getApiErrorMessage(signedIn.error) };

  return { ok: true };
};

export const logoutAction = async (): Promise<void> => {
  const cookiesList = await cookies();
  cookiesList.delete(AUTH_COOKIE);

  redirect(UrlGenerator.login());
};
