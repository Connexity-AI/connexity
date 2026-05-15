import { waitMs } from '@/utils/wait';

const DEV_BACKEND_FETCH_RETRIES = 3;
const DEV_BACKEND_FETCH_RETRY_DELAYS_MS = [150, 300];
const LOCAL_BACKEND_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);

function getRequestUrl(input: RequestInfo | URL): string | null {
  if (typeof input === 'string') {
    return input;
  }

  if (input instanceof URL) {
    return input.toString();
  }

  if (input instanceof Request) {
    return input.url;
  }

  return null;
}

function isDevelopmentBackendUrl(url: string | null): boolean {
  if (process.env.NODE_ENV !== 'development' || !url) {
    return false;
  }

  try {
    const parsed = new URL(url);
    return LOCAL_BACKEND_HOSTS.has(parsed.hostname);
  } catch {
    return false;
  }
}

function getErrorCode(error: unknown): string | undefined {
  if (!error || typeof error !== 'object') {
    return undefined;
  }

  const maybeCode = 'code' in error ? error.code : undefined;
  if (typeof maybeCode === 'string') {
    return maybeCode;
  }

  const maybeCause = 'cause' in error ? error.cause : undefined;
  if (maybeCause && typeof maybeCause === 'object' && 'code' in maybeCause) {
    const causeCode = maybeCause.code;
    if (typeof causeCode === 'string') {
      return causeCode;
    }
  }

  return undefined;
}

function shouldRetryBackendFetch(url: string | null, error: unknown): boolean {
  if (!isDevelopmentBackendUrl(url)) {
    return false;
  }

  const code = getErrorCode(error);
  if (code && ['ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT'].includes(code)) {
    return true;
  }

  return error instanceof TypeError && error.message.includes('fetch failed');
}

export async function fetchWithDevBackendRetry(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const requestUrl = getRequestUrl(input);

  for (let attempt = 1; attempt <= DEV_BACKEND_FETCH_RETRIES; attempt += 1) {
    try {
      return await fetch(input, init);
    } catch (error) {
      const canRetry =
        attempt < DEV_BACKEND_FETCH_RETRIES &&
        shouldRetryBackendFetch(requestUrl, error);

      if (!canRetry) {
        throw error;
      }

      const retryDelayMs = DEV_BACKEND_FETCH_RETRY_DELAYS_MS[attempt - 1] ?? 300;
      console.warn(
        `Retrying backend fetch after transient dev-server failure (attempt ${attempt + 1}/${DEV_BACKEND_FETCH_RETRIES}): ${requestUrl}`
      );
      await waitMs(retryDelayMs);
    }
  }

  throw new Error(`Backend fetch retries exhausted for ${requestUrl ?? 'unknown URL'}`);
}
