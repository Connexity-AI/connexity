'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';

import { signUpAction } from '@/actions/auth';
import { Field } from '@/components/auth/field';

import type { FC, FormEvent } from 'react';

const PASSWORD_MIN_LENGTH = 8;
const EMAIL_PATTERN = /.+@.+\..+/;

type SignUpError = 'emailTaken' | 'shortPassword' | 'other' | null;

export const SignUpForm: FC = () => {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<SignUpError>(null);
  const [message, setMessage] = useState('');
  const [isPending, startTransition] = useTransition();

  const clear = () => setError(null);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (password.length < PASSWORD_MIN_LENGTH) return setError('shortPassword');
    if (!name.trim() || !EMAIL_PATTERN.test(email.trim())) return;
    startTransition(async () => {
      const result = await signUpAction({
        full_name: name.trim(),
        email: email.trim(),
        password,
      });
      if (result.ok) return router.push(UrlGenerator.home());
      setError(result.reason);
      setMessage(result.message);
    });
  };

  return (
    <>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Field
          label="Name"
          autoComplete="name"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            clear();
          }}
        />
        <Field
          label="Work email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            clear();
          }}
          error={
            error === 'emailTaken' && (
              <>
                An account already uses this email.{' '}
                <Link href={UrlGenerator.login()} className="text-critical underline">
                  Sign in instead
                </Link>
              </>
            )
          }
        />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            clear();
          }}
          hint="At least 8 characters"
          error={error === 'shortPassword' && 'Use at least 8 characters.'}
        />
        <div className="flex flex-col gap-2 pt-2">
          {error === 'other' && <span className="text-label text-critical">{message}</span>}
          <Button type="submit" className="h-10 w-full" disabled={isPending}>
            Create account
          </Button>
        </div>
      </form>

      <span className="text-label text-ink-secondary">
        Already have an account?{' '}
        <Link href={UrlGenerator.login()} className="text-ink underline">
          Sign in
        </Link>
      </span>
    </>
  );
};

export default SignUpForm;
