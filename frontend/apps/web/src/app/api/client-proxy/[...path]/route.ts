import { NextRequest, NextResponse } from 'next/server';

import { getPublicEnv } from '@/config/process-env';

import { ClientProxyRouteParam } from '@/types/api';

// Note: endpoints to proxy requests from client to FastAPI backend, allowing us to attach HttpOnly cookies
// Only UsersService.readUserMe() actually used for now

const proxyHandler = async (request: NextRequest, { params }: ClientProxyRouteParam) => {
  const { path } = await params;

  const { API_URL } = getPublicEnv();

  // params.path just splits into array, this just joins back to string
  // path = ['api', 'v1', 'users', 'me'] -> http://api.localhost:8000/api/v1/users/me
  const backendUrl = `${API_URL}/${path.join('/')}`;

  // clone headers from client request
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => (headers[key] = value));

  const { method } = request;
  const body = ['GET', 'HEAD'].includes(method) ? undefined : await request.arrayBuffer();

  const apiResponse = await fetch(backendUrl, { method, headers, body });

  const data = await apiResponse.arrayBuffer();
  const response = new NextResponse(Buffer.from(data), { status: apiResponse.status });

  // copy headers from backend response, excluding ones automatically controlled by Node/Next.js internally
  const excludeHeaders = ['content-encoding', 'transfer-encoding', 'connection'];
  apiResponse.headers.forEach(
    (value, key) => !excludeHeaders.includes(key) && response.headers.set(key, value)
  );

  // optional: return error if response not ok
  if (!apiResponse.ok) {
    console.warn('Client proxy returned error:', apiResponse.status, backendUrl);
  }

  return response;
};

// add PUT, DELETE, PATCH if needed

export const GET = proxyHandler;

export const POST = proxyHandler;
