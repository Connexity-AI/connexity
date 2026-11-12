import { AuthService } from '@/client/sdk.gen';
import { getPublicEnv } from '@/config/process-env';

import type { FC } from 'react';

interface Props {
  /** Google refused or the person cancelled (`?error=google`). */
  failed: boolean;
}

const GoogleMark: FC = () => (
  <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden>
    <path
      fill="#EA4335"
      d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
    />
    <path
      fill="#4285F4"
      d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
    />
    <path
      fill="#FBBC05"
      d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
    />
    <path
      fill="#34A853"
      d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
    />
  </svg>
);

/**
 * "Continue with Google" and the divider. Absent when the deployment has no Google
 * settings. The Google mark's colours are the only third-party colours in the product.
 */
export const GoogleSignIn: FC<Props> = async ({ failed }) => {
  const status = await AuthService.googleStatus();
  if (!status.data?.enabled) return null;

  const { API_URL } = getPublicEnv();

  return (
    <>
      <div className="flex flex-col gap-2">
        {failed && (
          <span className="text-label text-critical">
            Google sign-in didn’t finish. Try again or use your email.
          </span>
        )}
        <a
          href={`${API_URL}/api/v1/auth/google/start`}
          className="flex h-10 w-full items-center justify-center gap-2.5 rounded-md border border-border-control text-body text-ink no-underline hover:bg-wash"
        >
          <GoogleMark />
          Continue with Google
        </a>
      </div>
      <div className="flex items-center gap-3 text-label text-ink-muted">
        <span className="h-px flex-1 bg-hairline" />
        or
        <span className="h-px flex-1 bg-hairline" />
      </div>
    </>
  );
};

export default GoogleSignIn;
