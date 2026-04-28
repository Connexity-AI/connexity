'use client';

import { useEffect, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@workspace/ui/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@workspace/ui/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@workspace/ui/components/ui/form';

import { createIntegration } from '@/actions/integrations';
import { isSuccessApiResult } from '@/utils/api';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

const formSchema = z.object({
  provider: z.enum(['retell']),
  name: z.string().min(1, 'Name is required'),
  api_key: z.string().min(1, 'API key is required'),
});

type FormValues = z.infer<typeof formSchema>;

type DialogState = 'form' | 'testing' | 'success' | 'error';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdded: (integration: IntegrationPublic) => void;
}

const INPUT_CLASS =
  'w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50';

export const AddIntegrationDialog: FC<Props> = ({ open, onOpenChange, onAdded }) => {
  const [dialogState, setDialogState] = useState<DialogState>('form');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { provider: 'retell', name: '', api_key: '' },
  });

  useEffect(() => {
    if (open) {
      form.reset({ provider: 'retell', name: '', api_key: '' });
      setDialogState('form');
      setErrorMessage('');
    }
  }, [open, form]);

  const handleOpenChange = (next: boolean) => {
    if (dialogState === 'testing' && !next) {
      return;
    }
    onOpenChange(next);
  };

  const onSubmit = async (values: FormValues) => {
    setDialogState('testing');
    setErrorMessage('');

    const result = await createIntegration(values);

    if (isSuccessApiResult(result)) {
      setDialogState('success');
      onAdded(result.data);
      setTimeout(() => onOpenChange(false), 1500);
      return;
    }

    const err = 'error' in result ? result.error : undefined;
    const msg =
      typeof err === 'object' && err !== null && 'detail' in err
        ? String((err as { detail: unknown }).detail)
        : 'Failed to add integration. Check your API key and try again.';
    setErrorMessage(msg);
    setDialogState('error');
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden [&>button:last-of-type]:hidden">
        <div className="px-6 py-4 border-b border-border">
          <DialogTitle className="text-sm font-medium text-foreground">
            Add Integration
          </DialogTitle>
        </div>

        {dialogState === 'success' ? (
          <div className="flex flex-col items-center justify-center gap-3 px-6 py-10">
            <CheckCircle className="w-10 h-10 text-green-500" />
            <p className="text-sm font-medium">Connection successful</p>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="p-6 space-y-4">
              {/* Provider */}
              <FormField
                control={form.control}
                name="provider"
                render={() => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground mb-2 block">
                      Provider
                    </FormLabel>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        className="px-3 py-2 rounded-lg border text-xs font-medium transition-colors border-primary bg-primary/10 text-foreground"
                      >
                        Retell
                      </button>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Integration Name */}
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground mb-2 block">
                      Integration Name
                    </FormLabel>
                    <FormControl>
                      <input
                        {...field}
                        type="text"
                        placeholder="e.g., Production Retell"
                        className={INPUT_CLASS}
                        disabled={dialogState === 'testing'}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* API Key */}
              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground mb-2 block">
                      API Key
                    </FormLabel>
                    <FormControl>
                      <input
                        {...field}
                        type="password"
                        placeholder="Enter your API key"
                        className={`${INPUT_CLASS} font-mono`}
                        disabled={dialogState === 'testing'}
                      />
                    </FormControl>
                    <div className="flex items-center justify-between mt-1">
                      <a
                        href="https://dashboard.retellai.com/settings/api-keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-primary hover:underline"
                      >
                        Get Retell API Key
                      </a>
                      <p className="text-[10px] text-muted-foreground/40">
                        Tip: Use &quot;test-error&quot; to demo error state
                      </p>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {dialogState === 'error' && errorMessage && (
                <div className="flex items-center gap-2.5 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3">
                  <XCircle className="w-4 h-4 shrink-0 text-destructive" />
                  <p className="text-sm text-destructive">Connection failed. Please check your API key.</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1"
                  onClick={() => onOpenChange(false)}
                  disabled={dialogState === 'testing'}
                >
                  Cancel
                </Button>
                <Button type="submit" className="flex-1" disabled={dialogState === 'testing'}>
                  {dialogState === 'testing' ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Testing connection…
                    </>
                  ) : (
                    'Add Integration'
                  )}
                </Button>
              </div>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
};
