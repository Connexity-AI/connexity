'use client';

import Link from 'next/link';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';

import { useRegister } from '@/hooks/use-register';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import type { FC } from 'react';

const INPUT_CLASS =
  'h-auto border-border bg-input-background px-3 py-2.5 text-sm placeholder:text-muted-foreground/50 focus-visible:ring-2 focus-visible:ring-ring/30';

const FormRegister: FC = () => {
  const { form, onSubmit, error, success, isPending } = useRegister();

  if (success) {
    return (
      <div className="flex flex-col gap-4 text-center">
        <h1 className="text-title font-medium">Registration successful</h1>
        <p className="text-sm text-muted-foreground">
          Your account has been created. You can now sign in.
        </p>
        <Link
          href={UrlGenerator.login()}
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <>
      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="email"
                    placeholder="you@example.com"
                    autoComplete="email"
                    disabled={isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="full_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Full Name</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    placeholder="Enter your name"
                    autoComplete="name"
                    disabled={isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder="At least 6 characters"
                    autoComplete="new-password"
                    disabled={isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="confirm_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm Password</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder="Repeat your password"
                    autoComplete="new-password"
                    disabled={isPending}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="w-full px-4 py-2 h-auto hover:bg-primary/90"
            disabled={isPending}
          >
            {isPending ? 'Creating account...' : 'Sign up'}
          </Button>
        </form>
      </Form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link
          href={UrlGenerator.login()}
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </>
  );
};

export default FormRegister;
