import { AuthService } from '@/client/sdk.gen';
import { GoogleSignIn } from '@/components/auth/google-sign-in';
import { SignInForm } from '@/components/auth/sign-in-form';

import type { FC } from 'react';

interface Props {
  searchParams: Promise<{ error?: string }>;
}

const LoginPage: FC<Props> = async ({ searchParams }) => {
  const { error } = await searchParams;
  const offered = await AuthService.googleStatus();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="m-0 text-title font-medium text-ink">Sign in</h1>
      <GoogleSignIn failed={error === 'google'} />
      <SignInForm canReset={offered.data?.password_reset === true} />
    </div>
  );
};

export default LoginPage;
