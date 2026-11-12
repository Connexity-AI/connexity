'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';

import { loginAction } from '@/actions/auth';
import { Field } from '@/components/auth/field';
import { isSuccessApiResult } from '@/utils/api';

import type { FC, FormEvent } from 'react';

export const SignInForm: FC = () => {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [failed, setFailed] = useState(false);
  const [isPending, startTransition] = useTransition();

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) return;
    startTransition(async () => {
      const result = await loginAction({ username: email.trim(), password });
      if (isSuccessApiResult(result)) router.push(UrlGenerator.home());
      else setFailed(true);
    });
  };

  return (
    <>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setFailed(false);
          }}
        />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setFailed(false);
          }}
        />
        <div className="flex flex-col gap-2 pt-2">
          {failed && (
            <span className="text-label text-critical">That email and password don’t match.</span>
          )}
          <Button type="submit" className="h-10 w-full" disabled={isPending}>
            Sign in
          </Button>
        </div>
      </form>

      <span className="text-label text-ink-secondary">
        New to Connexity?{' '}
        <Link href={UrlGenerator.register()} className="text-ink underline">
          Create an account
        </Link>
      </span>
    </>
  );
};

export default SignInForm;
