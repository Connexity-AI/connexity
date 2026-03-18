import { removeLeadingSlash } from '@/utils/path';
import { isServer } from '@/utils/runtime';
import { ROUTES } from '@/constants/routes';
import { getPublicEnv } from '@/config/process-env';

// import { waitMs } from '@/utils/wait';

import type { CreateClientConfig } from '@/client/client.gen';

const { CLIENT_PROXY } = ROUTES.API;

/** Runtime config. Runs and imported both on server and in browser. */
export const createClientConfig: CreateClientConfig = (config) => {
  const { API_URL } = getPublicEnv();

  return {
    ...config,
    baseUrl: API_URL,
    credentials: 'include',
    fetch: isServer() ? serverFetch : clientFetch,
  };
};

const serverFetch: typeof fetch = async (input, init = {}) => {
  // Note: Dynamic import to avoid bundling 'next/headers' on client
  const { cookies } = await import('next/headers');

  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join('; ');

  // Note: must append auth_cookie like this or content-type header will break in server actions
  const headers = new Headers(init.headers);
  headers.append('Cookie', cookieHeader);

  // test skeletons styling
  // await waitMs(3000);

  const response = fetch(input, { ...init, headers });

  return response;
};

/** Client-side fetch: forwards requests to api/client-proxy/[...path]/route.ts */
const clientFetch: typeof fetch = async (input, init = {}) => {
  const { API_URL } = getPublicEnv() as { API_URL: string };

  // hey-api sends absolute URL
  const url: string = typeof input === 'string' ? input : input.toString();

  // Normalize to relative URL
  // API_URL.length + 1 - removes leading slash, API_URL guaranteed not to have trailing slash
  const relativeUrl = url.startsWith(API_URL) ? url.slice(API_URL.length + 1) : url;

  // Build the proxy URL relative to Next.js API
  const proxyUrl = `${CLIENT_PROXY}${relativeUrl}`;

  const headers = new Headers(init.headers);

  return fetch(proxyUrl, { ...init, headers, credentials: 'include' });
};
