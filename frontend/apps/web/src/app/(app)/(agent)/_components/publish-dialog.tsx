'use client';

import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
} from '@workspace/ui/components/ui/form';

import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { usePublishDraft } from '@/app/(app)/(agent)/_hooks/use-publish-draft';

const publishSchema = z.object({
  name: z.string().optional(),
  description: z.string().optional(),
});

type PublishFormValues = z.infer<typeof publishSchema>;

export function PublishDialog() {
  const { isPublishDialogOpen, closePublishDialog } = useVersions();
  const { agentId } = useAgentEditFormActions();
  const { mutate: publish, isPending } = usePublishDraft(agentId);

  const form = useForm<PublishFormValues>({
    resolver: zodResolver(publishSchema),
    defaultValues: { name: '', description: '' },
  });

  const onSubmit = (data: PublishFormValues) => {
    const parts: string[] = [];
    if (data.name?.trim()) parts.push(data.name.trim());
    if (data.description?.trim()) parts.push(data.description.trim());
    const changeDescription = parts.join('\n') || undefined;

    publish(
      { change_description: changeDescription ?? null },
      {
        onSuccess: () => {
          form.reset();
          closePublishDialog();
        },
      },
    );
  };

  return (
    <Dialog open={isPublishDialogOpen} onOpenChange={(open) => !open && closePublishDialog()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Publish New Version</DialogTitle>
          <DialogDescription>
            Create a new published version from the current draft.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 py-2">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Version name (optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Improved escalation handling" {...field} />
                  </FormControl>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Describe what changed in this version..."
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button variant="outline" onClick={closePublishDialog} disabled={isPending} type="button">
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? 'Publishing...' : 'Publish'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
