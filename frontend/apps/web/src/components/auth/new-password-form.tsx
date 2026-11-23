'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Eye, EyeOff } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { setNewPasswordAction } from '@/actions/auth';
import { AuthScreen, LinkNoLongerWorks } from '@/components/auth/auth-screen';
import { Field } from '@/components/auth/field';

import type { FC, FormEvent } from 'react';

interface Props {
  token: string;
  /** The account the link is for. */
  email: string;
}

type Screen = 'form' | 'changed' | 'linkDead';

const TOO_SHORT = 'Use at least 8 characters.';
const TOO_LONG = 'Use at most 40 characters.';

/** "Set a new password", then "Password changed" with the person signed in. */
export const NewPasswordForm: FC<Props> = ({ token, email }) => {
  const [screen, setScreen] = useState<Screen>('form');
  const [password, setPassword] = useState('');
  const [shown, setShown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (isPending) return;
    if (password.length < 8) {
      setError(TOO_SHORT);
      return;
    }
    if (password.length > 40) {
      setError(TOO_LONG);
      return;
    }
    startTransition(async () => {
      const result = await setNewPasswordAction(token, password);
      if (result === 'saved') {
        setPassword('');
        setScreen('changed');
      } else if (result === 'linkDead') setScreen('linkDead');
      else if (result === 'shortPassword') setError(TOO_SHORT);
      else if (result === 'longPassword') setError(TOO_LONG);
      else setError('That didn’t work. Try again.');
    });
  };

  if (screen === 'changed')
    return (
      <AuthScreen
        title="Password changed"
        line="You’re signed out on your other devices. Your connected AI assistants keep working."
      >
        <div className="pt-2">
          <Button asChild className="h-10 w-full">
            <Link href={UrlGenerator.home()}>Continue to Connexity</Link>
          </Button>
        </div>
      </AuthScreen>
    );

  if (screen === 'linkDead') return <LinkNoLongerWorks />;

  const toggleLabel = shown ? 'Hide password' : 'Show password';

  return (
    <AuthScreen title="Set a new password" line={email}>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {/* Lets a password manager file the new password under the right account. */}
        <input
          type="email"
          value={email}
          autoComplete="username"
          readOnly
          tabIndex={-1}
          aria-hidden
          className="hidden"
        />
        <Field
          label="New password"
          type={shown ? 'text' : 'password'}
          autoComplete="new-password"
          value={password}
          hint="At least 8 characters"
          error={error}
          alert
          onChange={(e) => {
            setPassword(e.target.value);
            setError(null);
          }}
          trailing={
            <button
              type="button"
              onClick={() => setShown((now) => !now)}
              aria-label={toggleLabel}
              title={toggleLabel}
              className="flex size-10 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-ink-secondary hover:text-ink"
            >
              {shown ? (
                <EyeOff aria-hidden className="size-4" />
              ) : (
                <Eye aria-hidden className="size-4" />
              )}
            </button>
          }
        />
        <div className="pt-2">
          <Button
            type="submit"
            className="h-10 w-full"
            disabled={isPending}
            aria-busy={isPending || undefined}
          >
            {isPending ? 'Saving…' : 'Save password'}
          </Button>
        </div>
      </form>
    </AuthScreen>
  );
};

export default NewPasswordForm;
