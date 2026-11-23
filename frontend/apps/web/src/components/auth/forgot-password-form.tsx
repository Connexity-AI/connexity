'use client';

import { useEffect, useState, useTransition } from 'react';

import { Button } from '@workspace/ui/components/ui/button';

import { askForResetAction } from '@/actions/auth';
import { AuthScreen, BackToSignIn } from '@/components/auth/auth-screen';
import { Field, FieldAlert } from '@/components/auth/field';

import type { FC, FormEvent } from 'react';

/** Seconds before "Send again" is offered; the backend refuses sooner requests. */
const RESEND_AFTER = 45;
const FULL_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const INVALID_EMAIL = 'Enter a full email address, like alex@example.com.';
const FAILED = 'That didn’t work. Try again.';

/**
 * "Reset your password", then "Check your email" on the same page. What is shown
 * after sending is the same whether or not the email has an account.
 */
export const ForgotPasswordForm: FC = () => {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [rateLimited, setRateLimited] = useState(false);
  const [resendFailed, setResendFailed] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((left) => left - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const send = (address: string) => {
    startTransition(async () => {
      const result = await askForResetAction(address);
      if (result === 'invalidEmail') {
        setEmailError(INVALID_EMAIL);
        return;
      }
      if (result === 'failed') {
        // On "Check your email" there is no field to put this under.
        if (sentTo === null) setEmailError(FAILED);
        else setResendFailed(true);
        return;
      }
      setResendFailed(false);
      setSentTo(address);
      setRateLimited(result === 'rateLimited');
      setSecondsLeft(result === 'rateLimited' ? 0 : RESEND_AFTER);
    });
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (isPending) return;
    const address = email.trim();
    if (!FULL_EMAIL.test(address)) {
      setEmailError(INVALID_EMAIL);
      return;
    }
    send(address);
  };

  if (sentTo !== null) {
    const waiting = !rateLimited && secondsLeft > 0;
    return (
      <AuthScreen
        title="Check your email"
        line={
          <>
            If an account uses <strong className="font-medium text-ink">{sentTo}</strong>, a reset
            link is on its way. The link works once and expires in 1 hour.
          </>
        }
      >
        <div className="flex flex-col gap-2 pt-2">
          {rateLimited && <FieldAlert>Too many attempts. Try again later.</FieldAlert>}
          {resendFailed && !rateLimited && <FieldAlert>{FAILED}</FieldAlert>}
          <Button
            variant="secondary"
            className="h-10 w-full disabled:border-hairline disabled:text-ink-muted disabled:opacity-100"
            disabled={rateLimited || waiting || isPending}
            onClick={() => send(sentTo)}
          >
            {waiting ? `Send again in ${secondsLeft} s` : 'Send again'}
          </Button>
        </div>
        <BackToSignIn />
      </AuthScreen>
    );
  }

  return (
    <AuthScreen title="Reset your password" line="Enter your email and we’ll send you a link.">
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          error={emailError}
          alert
          onChange={(e) => {
            setEmail(e.target.value);
            setEmailError(null);
          }}
        />
        <div className="pt-2">
          <Button
            type="submit"
            className="h-10 w-full"
            disabled={isPending}
            aria-busy={isPending || undefined}
          >
            {isPending ? 'Sending…' : 'Send reset link'}
          </Button>
        </div>
      </form>
      <BackToSignIn />
    </AuthScreen>
  );
};

export default ForgotPasswordForm;
