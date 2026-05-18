'use client';

import { CheckCircle, Loader2, XCircle } from 'lucide-react';

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

import { PROVIDERS, useAddIntegrationDialog } from './use-add-integration-dialog';

import type { FC } from 'react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const INPUT_CLASS =
  'w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50';

export const AddIntegrationDialog: FC<Props> = ({ open, onOpenChange }) => {
  const { form, dialogState, errorMessage, selectedProvider, handleOpenChange, onSubmit } =
    useAddIntegrationDialog({ onOpenChange });

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden [&>button:last-of-type]:hidden">
        <div className="px-6 py-4 border-b border-border">
          <DialogTitle className="text-sm font-medium text-foreground">Add Integration</DialogTitle>
        </div>

        {dialogState === 'success' ? (
          <div className="flex flex-col items-center justify-center gap-3 px-6 py-10">
            <CheckCircle className="w-10 h-10 text-green-500" />
            <p className="text-sm font-medium">Connection successful</p>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={onSubmit} className="p-6 space-y-4">
              {/* Provider */}
              <FormField
                control={form.control}
                name="provider"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground mb-2 block">
                      Provider
                    </FormLabel>
                    <div className="grid grid-cols-3 gap-2">
                      {PROVIDERS.map((item) => (
                        <Button
                          key={item.value}
                          type="button"
                          variant="ghost"
                          size="sm"
                          className={`px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                            field.value === item.value
                              ? 'border-primary bg-primary/10 text-foreground hover:bg-primary/10 hover:text-foreground'
                              : 'border-border text-muted-foreground hover:bg-accent'
                          }`}
                          onClick={() => field.onChange(item.value)}
                          disabled={dialogState === 'testing'}
                        >
                          {item.label}
                        </Button>
                      ))}
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
                        placeholder={selectedProvider.placeholder}
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
                        href={selectedProvider.docsHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-primary hover:underline"
                      >
                        {selectedProvider.docsLabel}
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
                  <p className="text-sm text-destructive">
                    Connection failed. Please check your API key.
                  </p>
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
