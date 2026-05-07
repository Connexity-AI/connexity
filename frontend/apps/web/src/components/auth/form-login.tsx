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

import { useLogin } from '@/hooks/use-login';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import type { FC } from 'react';

const INPUT_CLASS =
  'h-auto border-border bg-input-background px-3 py-2.5 text-sm placeholder:text-muted-foreground/50 focus-visible:ring-2 focus-visible:ring-ring/30';

const FormLogin: FC = () => {
  const { form, onSubmit, error, isPending } = useLogin();

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
            name="username"
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
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder="Your password"
                    autoComplete="current-password"
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
            {isPending ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>
      </Form>

      <p className="text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{' '}
        <Link
          href={UrlGenerator.register()}
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Sign up
        </Link>
      </p>
    </>
  );
};

export default FormLogin;
