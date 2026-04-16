'use client';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { Form } from '@workspace/ui/components/ui/form';

import { useAgentGuidelinesForm } from '@/app/(app)/(agent)/_hooks/use-agent-guidelines-form';

import { GuidelinesTextareaField } from './guidelines-textarea-field';

interface GuidelinesDialogProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GuidelinesDialog({ agentId, open, onOpenChange }: GuidelinesDialogProps) {
  const {
    form,
    onSubmit,
    isLoading,
    isSaving,
    isResetting,
    isDefault,
    resetToDefault,
    queryError,
  } = useAgentGuidelinesForm({
    agentId,
    enabled: open,
    onSaved: () => onOpenChange(false),
  });

  const isBusy = isSaving || isResetting;
  const canSave = form.formState.isDirty && !isBusy && !queryError;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="left-0 top-0 translate-x-0 translate-y-0 w-screen h-screen max-w-none rounded-none border-0 sm:rounded-none flex flex-col gap-0 p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <div className="flex items-center gap-2">
            <DialogTitle>Assistant Guidelines</DialogTitle>
            {isDefault && (
              <span className="text-xs text-muted-foreground rounded-full border px-2 py-0.5">
                Using default
              </span>
            )}
          </div>
          <DialogDescription>
            These instructions steer how the assistant rewrites and suggests prompts
            for this agent.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={onSubmit}
            className="flex flex-col flex-1 min-h-0 px-6 pt-4"
          >
            <GuidelinesTextareaField
              control={form.control}
              isLoading={isLoading}
              queryError={queryError}
            />

            <DialogFooter className="py-4 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => void resetToDefault()}
                disabled={isDefault || isBusy || isLoading}
              >
                {isResetting ? 'Resetting…' : 'Reset to default'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isBusy}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!canSave}>
                {isSaving ? 'Saving…' : 'Save'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
