import { GoogleSignIn } from '@/components/auth/google-sign-in';
import { SignUpForm } from '@/components/auth/sign-up-form';

import type { FC } from 'react';

interface Props {
  searchParams: Promise<{ error?: string }>;
}

const RegisterPage: FC<Props> = async ({ searchParams }) => {
  const { error } = await searchParams;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="m-0 text-title font-medium text-ink">Create an account</h1>
      <GoogleSignIn failed={error === 'google'} />
      <SignUpForm />
    </div>
  );
};

export default RegisterPage;
