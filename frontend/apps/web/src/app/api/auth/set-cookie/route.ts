import { NextResponse } from 'next/server';

import { AUTH_COOKIE } from '@/constants/auth';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { getPublicEnv } from '@/config/process-env';

export const GET = async (request: Request): Promise<Response> => {
  const { SITE_URL, NODE_ENV } = getPublicEnv();
  const isProd = NODE_ENV === 'production';

  const url = new URL(request.url);

  const accessToken = url.searchParams.get('access_token');
  const expiresParam = url.searchParams.get('expires');

  const hasAllData = accessToken && expiresParam;
  if (!hasAllData) {
    const loginUrl = new URL(`${UrlGenerator.login()}?error=missing_auth_token`, SITE_URL);
    return NextResponse.redirect(loginUrl, { status: 302 });
  }

  // Convert Unix timestamp (seconds) to a JS Date object
  const expiresDate = new Date(Number(expiresParam) * 1000);

  const redirectUrl = new URL(UrlGenerator.home(), SITE_URL);
  const response = NextResponse.redirect(redirectUrl, { status: 302 });

  response.cookies.set({
    name: AUTH_COOKIE,

    // passed from backend
    value: accessToken,
    expires: expiresDate,

    // frontend-specific
    httpOnly: true,
    secure: isProd,

    // host-only
    path: '/',
    sameSite: 'lax',
    domain: undefined,
  });

  return response;
};
