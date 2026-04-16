import { NextRequest, NextResponse } from 'next/server';

import { getPublicEnv } from '@/config/process-env';

// Proxies authenticated client-side requests to the FastAPI backend so the
// browser can attach the HttpOnly `auth_cookie`. Preserves the full pathname
// (including trailing slashes that FastAPI route definitions rely on) and the
// query string from the incoming request.

const PROXY_PREFIX = '/api/client-proxy';

const HOP_BY_HOP_REQUEST_HEADERS = new Set(['host', 'connection']);
const HOP_BY_HOP_RESPONSE_HEADERS = new Set([
  'content-encoding',
  'transfer-encoding',
  'connection',
]);

const proxyHandler = async (request: NextRequest) => {
  const { API_URL } = getPublicEnv();

  const { pathname, search } = request.nextUrl;
  const relativePath = pathname.startsWith(PROXY_PREFIX)
    ? pathname.slice(PROXY_PREFIX.length)
    : pathname;
  const backendUrl = `${API_URL}${relativePath}${search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_REQUEST_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const { method } = request;
  const body = ['GET', 'HEAD'].includes(method) ? undefined : await request.arrayBuffer();

  const apiResponse = await fetch(backendUrl, { method, headers, body });

  if (!apiResponse.ok) {
    console.warn('Client proxy returned error:', apiResponse.status, backendUrl);
  }

  // Stream the backend response body through so SSE endpoints are not buffered
  const response = new NextResponse(apiResponse.body, { status: apiResponse.status });

  apiResponse.headers.forEach(
    (value, key) =>
      !HOP_BY_HOP_RESPONSE_HEADERS.has(key.toLowerCase()) && response.headers.set(key, value)
  );

  return response;
};

export const GET = proxyHandler;

export const POST = proxyHandler;

export const PUT = proxyHandler;

export const PATCH = proxyHandler;

export const DELETE = proxyHandler;
