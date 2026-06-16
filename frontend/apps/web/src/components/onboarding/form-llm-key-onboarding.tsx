'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { updateLlmCredentials } from '@/actions/company';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { FC } from 'react';

const INPUT_CLASS =
  'h-auto border-border bg-input-background px-3 py-2.5 text-sm placeholder:text-muted-foreground/50 focus-visible:ring-2 focus-visible:ring-ring/30';

const llmKeyOnboardingSchema = z
  .object({
    provider: z.enum(['openai', 'anthropic']),
    api_key: z.string().min(10, 'Paste your API key'),
  })
  .refine((value) => value.api_key.trim().length > 0, {
    message: 'API key is required',
    path: ['api_key'],
  });

type LlmKeyOnboardingValues = z.infer<typeof llmKeyOnboardingSchema>;

const resolver = zodResolver(llmKeyOnboardingSchema);
const defaultValues: LlmKeyOnboardingValues = { provider: 'openai', api_key: '' };

const FormLlmKeyOnboarding: FC = () => {
  const form = useForm<LlmKeyOnboardingValues>({ resolver, defaultValues });
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: async (values: LlmKeyOnboardingValues) => {
      const body =
        values.provider === 'openai'
          ? { openai_api_key: values.api_key, preferred_llm_provider: 'openai' as const }
          : { anthropic_api_key: values.api_key, preferred_llm_provider: 'anthropic' as const };
      return updateLlmCredentials(body);
    },
    onSuccess: (result) => {
      if (isSuccessApiResult(result)) {
        router.replace(UrlGenerator.dashboard());
        router.refresh();
      }
    },
  });

  const onSubmit = (values: LlmKeyOnboardingValues) => mutation.mutate(values);

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

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
            name="provider"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Provider</FormLabel>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={mutation.isPending}
                >
                  <FormControl>
                    <SelectTrigger className="h-auto px-3 py-2.5 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  Pick whichever you have a key for — features are interchangeable.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="api_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>API key</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder="sk-..."
                    autoComplete="off"
                    spellCheck={false}
                    disabled={mutation.isPending}
                  />
                </FormControl>
                <FormDescription>
                  Stored encrypted. You can rotate it later in Settings.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Validating…' : 'Continue'}
          </Button>
        </form>
      </Form>
    </>
  );
};

export default FormLlmKeyOnboarding;
