'use client';

import { startTransition, useActionState, useEffect, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useForm } from 'react-hook-form';

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

import { profilePasswordUpdateAction } from '@/actions/profile';
import { Message } from '@/client/types.gen';
import { profilePasswordUpdateSchema } from '@/schemas/forms';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { EVENTS } from '@/constants/events';

import { AlertProfileUpdateEventArgs } from '@/types/events';
import type { ProfilePasswordUpdateFormValues } from '@/types/forms';
import type { FC, FormEvent } from 'react';

const { ALERT_PROFILE_UPDATE_SHOW } = EVENTS;

const resolver = zodResolver(profilePasswordUpdateSchema);

const FormPasswordUpdate: FC = () => {
  const initialState = { data: undefined };
  const [state, formAction, isPending] = useActionState(profilePasswordUpdateAction, initialState);

  // Don't pre-populate passwords
  const defaultValues: ProfilePasswordUpdateFormValues = {
    current_password: '',
    new_password: '',
    confirm_password: '',
  } as const;

  const form = useForm<ProfilePasswordUpdateFormValues>({ resolver, defaultValues });

  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const isSuccess = isSuccessApiResult(state);
  const isError = isErrorApiResult(state);

  const showAlert = (alertArgs: AlertProfileUpdateEventArgs) => {
    const showEvent = new CustomEvent(ALERT_PROFILE_UPDATE_SHOW, { detail: alertArgs });
    window.dispatchEvent(showEvent);
  };

  useEffect(() => {
    let alertArgs: AlertProfileUpdateEventArgs | null = null;

    switch (true) {
      case isSuccess:
        alertArgs = {
          variant: 'success',
          message: (state.data as Message).message,
        };
        break;

      case isError:
        alertArgs = { variant: 'destructive', message: getApiErrorMessage(state.error) };
        break;

      default:
        alertArgs = null;
    }

    if (alertArgs) showAlert(alertArgs);
  }, [isSuccess, isError, state]);

  const validateAndSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    form.handleSubmit(() => {
      const formElement = event.target as HTMLFormElement;
      const formData = new FormData(formElement);

      startTransition(() => {
        formAction(formData);
        form.reset();
      });
    })(event);
  };

  return (
    <Form {...form}>
      <form action={formAction} onSubmit={validateAndSubmit} className="space-y-6">
        <FormField
          control={form.control}
          name="current_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Current Password *</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showCurrentPassword ? 'text' : 'password'}
                    placeholder="Enter your current password..."
                    {...field}
                  />
                </FormControl>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                >
                  {showCurrentPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="new_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>New Password *</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showNewPassword ? 'text' : 'password'}
                    placeholder="Enter your new password..."
                    {...field}
                  />
                </FormControl>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                >
                  {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirm_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm New Password *</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm your new password..."
                    {...field}
                  />
                </FormControl>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end">
          <Button type="submit" disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Updating...
              </>
            ) : (
              'Update Password'
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
};

export default FormPasswordUpdate;
