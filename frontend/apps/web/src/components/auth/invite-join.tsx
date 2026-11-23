'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';

import {
  acceptInviteAction,
  declineInviteAction,
  signInAndJoinAction,
  signUpAndJoinAction,
  switchAccountForInviteAction,
} from '@/actions/auth';
import { AuthScreen } from '@/components/auth/auth-screen';
import { Field } from '@/components/auth/field';

import type { JoinResult } from '@/actions/auth';
import type { InviteLook } from '@/client/types.gen';
import type { FC, FormEvent, ReactNode } from 'react';

interface Props {
  token: string;
  invite: InviteLook;
  /** The email of the session in this browser, if any. */
  signedInAs: string | null;
  /** "Continue with Google" and its divider; nothing when Google is not offered. */
  google: ReactNode;
}

const plural = (n: number) => `${n} ${n === 1 ? 'workspace' : 'workspaces'}`;

/**
 * Joining an agency from an invite, in every state: a new account, an account that
 * signs in, signed in with the invited email, signed in with another one.
 */
export const InviteJoin: FC<Props> = ({ token, invite, signedInAs, google }) => {
  const router = useRouter();
  const [mode, setMode] = useState<'new' | 'existing'>(invite.has_account ? 'existing' : 'new');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [shortPassword, setShortPassword] = useState(false);
  const [dead, setDead] = useState(false);
  const [isPending, startTransition] = useTransition();
  const title = `Join ${invite.agency_name}`;

  const finish = (result: JoinResult) => {
    if (result.ok) {
      router.push(UrlGenerator.home());
      router.refresh();
    } else if (result.reason === 'linkDead') setDead(true);
    else if (result.reason === 'shortPassword') setShortPassword(true);
    else if (result.reason === 'credentials') setProblem('That email and password don’t match.');
    else setProblem(result.message);
  };
  const run = (action: () => Promise<JoinResult>) => {
    if (isPending) return;
    setProblem(null);
    startTransition(async () => finish(await action()));
  };

  if (dead)
    return (
      <AuthScreen
        title="This invite no longer works"
        line="Ask the person who invited you for a new one."
      >
        {null}
      </AuthScreen>
    );

  if (signedInAs && signedInAs.toLowerCase() !== invite.email.toLowerCase())
    return (
      <AuthScreen
        title={title}
        line={
          <>
            This invite is for <strong className="font-medium text-ink">{invite.email}</strong>.
            You’re signed in as <strong className="font-medium text-ink">{signedInAs}</strong>.
          </>
        }
      >
        <div className="pt-2">
          <Button
            className="h-10 w-full"
            disabled={isPending}
            onClick={() => startTransition(() => switchAccountForInviteAction(token))}
          >
            Sign in with another account
          </Button>
        </div>
      </AuthScreen>
    );

  // Joining and declining both end on the app: the invite is settled either way.
  if (signedInAs)
    return (
      <AuthScreen title={title} line={`You’ll get access to ${plural(invite.workspaces)}`}>
        <div className="flex flex-col gap-2 pt-2">
          {problem && <span className="text-label text-critical">{problem}</span>}
          <Button
            className="h-10 w-full"
            disabled={isPending}
            onClick={() => run(() => acceptInviteAction(token))}
          >
            Join
          </Button>
          <Button
            variant="secondary"
            className="h-10 w-full"
            disabled={isPending}
            onClick={() => run(() => declineInviteAction(token))}
          >
            Decline
          </Button>
        </div>
      </AuthScreen>
    );

  const isNew = mode === 'new';
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (isNew) {
      if (!name.trim()) return;
      if (password.length < 8) return setShortPassword(true);
      run(() => signUpAndJoinAction(token, name.trim(), password));
    } else if (password) run(() => signInAndJoinAction(token, password));
  };

  return (
    <AuthScreen title={title} line={`${invite.invited_by ?? 'Someone'} invited ${invite.email}`}>
      {google}
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {isNew && (
          <Field
            label="Name"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <Field
          label="Email"
          type="email"
          value={invite.email}
          readOnly
          autoComplete="username"
          className="text-ink-secondary"
        />
        <Field
          label="Password"
          type="password"
          autoComplete={isNew ? 'new-password' : 'current-password'}
          value={password}
          hint={isNew ? 'At least 8 characters' : undefined}
          error={shortPassword ? 'Use at least 8 characters.' : undefined}
          labelAction={
            !isNew && (
              <Link
                href={UrlGenerator.forgotPassword()}
                className="text-label text-ink-secondary no-underline hover:text-ink hover:underline"
              >
                Forgot password?
              </Link>
            )
          }
          onChange={(e) => {
            setPassword(e.target.value);
            setShortPassword(false);
            setProblem(null);
          }}
        />
        <div className="flex flex-col gap-2 pt-2">
          {problem && <span className="text-label text-critical">{problem}</span>}
          <Button type="submit" className="h-10 w-full" disabled={isPending}>
            {isNew ? 'Create account and join' : 'Sign in'}
          </Button>
        </div>
      </form>
      <span className="text-label text-ink-secondary">
        {isNew ? 'Already have an account? ' : 'New to Connexity? '}
        <button
          type="button"
          onClick={() => {
            setMode(isNew ? 'existing' : 'new');
            setPassword('');
            setProblem(null);
            setShortPassword(false);
          }}
          className="cursor-pointer border-0 bg-transparent p-0 text-label text-ink underline"
        >
          {isNew ? 'Sign in' : 'Create an account'}
        </button>
      </span>
    </AuthScreen>
  );
};

export default InviteJoin;
