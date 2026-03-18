'use client';

import { startTransition, useActionState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';

import { Alert, AlertDescription } from '@workspace/ui/components/ui/alert';
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

import { registerAction } from '@/actions/auth';
import { registerFormSchema } from '@/schemas/forms';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { ROUTES } from '@/constants/routes';

import { ApiResult } from '@/types/api';
import type { RegisterFormValues } from '@/types/forms';
import type { FC, FormEvent } from 'react';

const { LOGIN } = ROUTES;

const defaultValues: RegisterFormValues = {
  email: '',
  full_name: '',
  password: '',
  confirm_password: '',
} as const;

const resolver = zodResolver(registerFormSchema);

const FormRegister: FC = () => {
  const router = useRouter();
  const form = useForm<RegisterFormValues>({ resolver, defaultValues });

  const initialState: ApiResult = { data: undefined };

  const [state, formAction, isPending] = useActionState(registerAction, initialState);

  const isError = isErrorApiResult(state);
  const isSuccess = isSuccessApiResult(state);

  useEffect(() => {
    if (!isSuccess) return;

    router.push(LOGIN);
  }, [isSuccess, router]);

  const validateAndSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    form.handleSubmit(() => {
      const formElement = event.target as HTMLFormElement;
      const formData = new FormData(formElement);

      startTransition(() => formAction(formData));
    })(event);
  };

  return (
    <Form {...form}>
      <form action={formAction} onSubmit={validateAndSubmit} className="space-y-6">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="you@example.com" {...field} disabled={isPending} />
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
                <Input placeholder="Enter your name" {...field} disabled={isPending} />
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
                  type="password"
                  placeholder="Choose a password"
                  {...field}
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
              <FormLabel>Confirm password</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="Confirm password"
                  {...field}
                  disabled={isPending}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {isSuccess && (
          <p className="text-sm font-medium text-green-600">
            Registration successful. Redirecting...
          </p>
        )}

        {isError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{getApiErrorMessage(state.error)}</AlertDescription>
          </Alert>
        )}

        <p className="text-sm">
          Already have an account?{' '}
          <Link href={LOGIN} className="text-teal-600 hover:text-teal-700 hover:underline">
            Log in
          </Link>
        </p>

        <Button
          type="submit"
          disabled={isPending}
          className="w-full h-12 bg-teal-600 hover:bg-teal-700 font-medium"
        >
          {isPending ? 'Registering...' : 'Create Account'}
        </Button>
      </form>
    </Form>
  );
};

export default FormRegister;
