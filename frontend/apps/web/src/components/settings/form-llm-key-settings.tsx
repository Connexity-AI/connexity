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
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { CompanyLlmCredentialsPublic } from '@/client/types.gen';
import type { FC } from 'react';

const INPUT_CLASS =
  'h-auto border-border bg-input-background px-3 py-2.5 text-sm placeholder:text-muted-foreground/50 focus-visible:ring-2 focus-visible:ring-ring/30';

const llmKeySettingsSchema = z.object({
  openai_api_key: z.string().optional(),
  anthropic_api_key: z.string().optional(),
  preferred_llm_provider: z.enum(['openai', 'anthropic']),
});

type LlmKeySettingsValues = z.infer<typeof llmKeySettingsSchema>;

const resolver = zodResolver(llmKeySettingsSchema);

interface Props {
  current: CompanyLlmCredentialsPublic | null;
  onSaved?: () => void;
}

const FormLlmKeySettings: FC<Props> = ({ current, onSaved }) => {
  const defaultValues: LlmKeySettingsValues = {
    openai_api_key: '',
    anthropic_api_key: '',
    preferred_llm_provider: current?.preferred_llm_provider ?? 'openai',
  };
  const form = useForm<LlmKeySettingsValues>({ resolver, defaultValues });
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: async (values: LlmKeySettingsValues) => {
      // Only forward fields the user actually changed. Empty string is the
      // explicit "clear" signal, so it has to be preserved verbatim; ``null``
      // means "leave alone" (we omit the field instead of sending null because
      // the SDK serializes null as ``null``).
      const body: Record<string, unknown> = {
        preferred_llm_provider: values.preferred_llm_provider,
      };
      if (values.openai_api_key && values.openai_api_key.trim().length > 0) {
        body.openai_api_key = values.openai_api_key;
      }
      if (values.anthropic_api_key && values.anthropic_api_key.trim().length > 0) {
        body.anthropic_api_key = values.anthropic_api_key;
      }
      return updateLlmCredentials(body);
    },
    onSuccess: (result) => {
      if (isSuccessApiResult(result)) {
        form.reset({
          openai_api_key: '',
          anthropic_api_key: '',
          preferred_llm_provider: result.data.preferred_llm_provider ?? 'openai',
        });
        router.refresh();
        onSaved?.();
      }
    },
  });

  const onSubmit = (values: LlmKeySettingsValues) => mutation.mutate(values);

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;
  const success = mutation.data ? isSuccessApiResult(mutation.data) : false;

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600">
          Saved.
        </div>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-5">
          <FormField
            control={form.control}
            name="openai_api_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>OpenAI key</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder={current?.openai_api_key_masked ?? 'sk-...'}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={mutation.isPending}
                  />
                </FormControl>
                <FormDescription>
                  {current?.openai_api_key_masked
                    ? `Currently: ${current.openai_api_key_masked}. Leave blank to keep.`
                    : 'Not set. Paste an OpenAI key to enable OpenAI features.'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="anthropic_api_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Anthropic key</FormLabel>
                <FormControl>
                  <Input
                    className={INPUT_CLASS}
                    {...field}
                    type="password"
                    placeholder={current?.anthropic_api_key_masked ?? 'sk-ant-...'}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={mutation.isPending}
                  />
                </FormControl>
                <FormDescription>
                  {current?.anthropic_api_key_masked
                    ? `Currently: ${current.anthropic_api_key_masked}. Leave blank to keep.`
                    : 'Not set. Paste an Anthropic key to enable Anthropic features.'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="preferred_llm_provider"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Preferred provider</FormLabel>
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
                  Default when a feature doesn&apos;t specify a provider.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving…' : 'Save'}
          </Button>
        </form>
      </Form>
    </div>
  );
};

export default FormLlmKeySettings;
