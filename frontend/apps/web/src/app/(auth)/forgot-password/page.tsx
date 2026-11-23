import { notFound } from 'next/navigation';

import { AuthService } from '@/client/sdk.gen';
import { ForgotPasswordForm } from '@/components/auth/forgot-password-form';

import type { FC } from 'react';

/** Ask for a reset link (designs/screens/Connexity Password Reset.dc.html, 2 and 3). */
const ForgotPasswordPage: FC = async () => {
  const offered = await AuthService.googleStatus();
  if (offered.data?.password_reset !== true) notFound();

  return <ForgotPasswordForm />;
};

export default ForgotPasswordPage;
