import { PasswordResetService } from '@/client/sdk.gen';
import { LinkNoLongerWorks } from '@/components/auth/auth-screen';
import { NewPasswordForm } from '@/components/auth/new-password-form';

import type { FC } from 'react';

interface Props {
  params: Promise<{ token: string }>;
}

/** Opened from the reset email (designs/screens/Connexity Password Reset.dc.html, 4 to 6). */
const ResetPasswordPage: FC<Props> = async ({ params }) => {
  const { token } = await params;
  const link = await PasswordResetService.passwordResetLookAtResetLink({ path: { token } });

  if (!link.data) return <LinkNoLongerWorks />;

  return <NewPasswordForm token={token} email={link.data.email} />;
};

export default ResetPasswordPage;
