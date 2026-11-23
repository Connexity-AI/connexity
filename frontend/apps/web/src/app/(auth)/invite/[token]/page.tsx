import { InvitesService, UsersService } from '@/client/sdk.gen';
import { AuthScreen } from '@/components/auth/auth-screen';
import { GoogleSignIn } from '@/components/auth/google-sign-in';
import { InviteJoin } from '@/components/auth/invite-join';

import type { FC } from 'react';

interface Props {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ error?: string }>;
}

/** Who is signed in, if anyone; a request without a session is refused, not an error. */
const signedInEmail = async (): Promise<string | null> => {
  try {
    const result = await UsersService.readUserMe();
    return result.data?.email ?? null;
  } catch {
    return null;
  }
};

/** Accept an agency invite (designs/screens/Connexity Agency Members.dc.html, 7a to 7e). */
const InvitePage: FC<Props> = async ({ params, searchParams }) => {
  const { token } = await params;
  const { error } = await searchParams;
  const [look, me] = await Promise.all([
    InvitesService.lookAtInvite({ path: { token } }),
    signedInEmail(),
  ]);

  if (!look.data)
    return (
      <AuthScreen
        title="This invite no longer works"
        line="Ask the person who invited you for a new one."
      >
        {null}
      </AuthScreen>
    );

  return (
    <InviteJoin
      token={token}
      invite={look.data}
      signedInAs={me}
      google={<GoogleSignIn failed={error === 'google'} invite={token} />}
    />
  );
};

export default InvitePage;
