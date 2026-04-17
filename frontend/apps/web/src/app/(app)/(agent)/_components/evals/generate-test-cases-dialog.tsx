'use client';

import { useEffect } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { AlertTriangle, GitBranch, Sparkles } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Alert, AlertDescription, AlertTitle } from '@workspace/ui/components/ui/alert';
import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import { Label } from '@workspace/ui/components/ui/label';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';

const MIN_COUNT = 1;
const MAX_COUNT = 200;
const DEFAULT_COUNT = 10;

const formSchema = z.object({
  count: z
    .number()
    .int()
    .min(MIN_COUNT, `Must be at least ${MIN_COUNT}`)
    .max(MAX_COUNT, `Must be at most ${MAX_COUNT}`),
});

type FormValues = z.infer<typeof formSchema>;

interface GenerateTestCasesDialogProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (count: number) => void;
}

export function GenerateTestCasesDialog({
  agentId,
  open,
  onOpenChange,
  onGenerate,
}: GenerateTestCasesDialogProps) {
  const { data: agent } = useAgent(agentId);
  const { data: versions, isLoading: versionsLoading } = useAgentVersions(agentId);

  const hasPublishedVersion = !versionsLoading && (versions?.count ?? 0) > 0;

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { count: DEFAULT_COUNT },
  });

  useEffect(() => {
    if (open) form.reset({ count: DEFAULT_COUNT });
  }, [open, form]);

  const onSubmit = (data: FormValues) => {
    if (!hasPublishedVersion) return;
    onGenerate(data.count);
    onOpenChange(false);
  };

  const count = form.watch('count');
  const canSubmit = hasPublishedVersion && count >= MIN_COUNT && count <= MAX_COUNT;
  const estimatedMinutes = Math.max(1, Math.ceil((count || 0) / 2));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-125 p-0 gap-0 overflow-hidden">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col">
            <DialogHeader className="flex-row items-center gap-2.5 space-y-0 px-5 py-4 border-b border-border">
              <div className="w-7 h-7 rounded-md bg-violet-500/10 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              </div>
              <DialogTitle className="text-sm font-normal text-foreground">
                Generate Test Cases
              </DialogTitle>
            </DialogHeader>

            <div className="px-5 py-5 space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <GitBranch className="w-3.5 h-3.5 text-muted-foreground" />
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                    Inputs
                  </Label>
                </div>
                <div className="rounded-lg border border-border bg-accent/20">
                  <div className="px-3 py-2.5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-3.5 h-3.5 text-muted-foreground/60" />
                      <span className="text-xs text-foreground">Agent Version</span>
                    </div>
                    <span className="text-xs font-mono text-foreground">
                      {agent ? `v${agent.version}` : '—'}
                    </span>
                  </div>
                  <div className="px-3 py-2 border-t border-border/50 bg-accent/10">
                    <p className="text-[10px] text-muted-foreground/60 leading-relaxed">
                      Agent prompt, model settings, and tool calls from this version will be used to
                      generate test cases
                    </p>
                  </div>
                </div>
              </div>

              {!versionsLoading && !hasPublishedVersion && (
                <Alert variant="destructive">
                  <AlertTriangle className="w-4 h-4" />
                  <AlertTitle>No published version</AlertTitle>
                  <AlertDescription>
                    Publish a version of this agent before generating test cases.
                  </AlertDescription>
                </Alert>
              )}

              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-muted-foreground" />
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                    Output
                  </Label>
                </div>
                <FormField
                  control={form.control}
                  name="count"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <Label htmlFor="count" className="text-xs text-muted-foreground">
                        Number of test cases to generate
                      </Label>
                      <FormControl>
                        <Input
                          id="count"
                          type="number"
                          min={MIN_COUNT}
                          max={MAX_COUNT}
                          className="h-9 text-sm"
                          name={field.name}
                          ref={field.ref}
                          onBlur={field.onBlur}
                          value={Number.isFinite(field.value) ? field.value : ''}
                          onChange={(e) => {
                            const parsed = Number.parseInt(e.target.value, 10);
                            field.onChange(Number.isNaN(parsed) ? 0 : parsed);
                          }}
                        />
                      </FormControl>
                      <p className="text-[10px] text-muted-foreground/50">
                        Between {MIN_COUNT}–{MAX_COUNT} test cases · Estimated time: ~
                        {estimatedMinutes} min
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border bg-accent/10">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" className="h-8 text-xs gap-1.5" disabled={!canSubmit}>
                <Sparkles className="w-3.5 h-3.5" />
                Generate {count || ''} test case{count === 1 ? '' : 's'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
