'use client';

import { useRouter } from 'next/navigation';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';

import { loginAction } from '@/actions/auth';
import { loginFormSchema } from '@/schemas/forms';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import type { LoginFormValues } from '@/types/forms';

const resolver = zodResolver(loginFormSchema);

const defaultValues: LoginFormValues = {
  username: '',
  password: '',
} as const;

export function useLogin() {
  const router = useRouter();

  const form = useForm<LoginFormValues>({ resolver, defaultValues });

  const mutation = useMutation({
    mutationFn: loginAction,
    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      router.push(UrlGenerator.home());
    },
  });

  const onSubmit = (values: LoginFormValues) => mutation.mutate(values);

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return { form, onSubmit, error, isPending: mutation.isPending };
}
