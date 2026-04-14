import { isServer } from '@/utils/runtime';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { getPublicEnv } from '@/config/process-env';

// import { waitMs } from '@/utils/wait';

import type { CreateClientConfig } from '@/client/client.gen';

const CLIENT_PROXY = UrlGenerator.apiClientProxy();

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
    .map((cookie) => `${cookie.name}=${cookie.value}`)
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

  // hey-api may pass a string URL, a URL object, or a Request (e.g. from the SSE client)
  const originalUrl: string =
    typeof input === 'string'
      ? input
      : input instanceof Request
        ? input.url
        : input.toString();

  // Normalize to relative URL
  // API_URL.length + 1 - removes leading slash, API_URL guaranteed not to have trailing slash
  const relativeUrl = originalUrl.startsWith(API_URL)
    ? originalUrl.slice(API_URL.length + 1)
    : originalUrl;

  // Build the proxy URL relative to Next.js API
  const proxyUrl = `${CLIENT_PROXY}${relativeUrl}`;

  // When hey-api's SSE client passes a Request, re-issue the fetch against the
  // proxy URL. Rebuilding via `new Request(proxyUrl, input)` leaks internal
  // state from the original origin (causing ERR_ALPN_NEGOTIATION_FAILED), so
  // copy the relevant fields onto a plain init object instead.
  if (input instanceof Request) {
    const bodyless = input.method === 'GET' || input.method === 'HEAD';
    const body = bodyless ? undefined : await input.arrayBuffer();
    return fetch(proxyUrl, {
      method: input.method,
      headers: input.headers,
      body,
      signal: input.signal,
      redirect: input.redirect,
      credentials: 'include',
    });
  }

  const headers = new Headers(init.headers);

  return fetch(proxyUrl, { ...init, headers, credentials: 'include' });
};
