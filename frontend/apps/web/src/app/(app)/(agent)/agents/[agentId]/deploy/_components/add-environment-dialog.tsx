'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';

import { AlertTriangle } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';

import { useIntegrations } from '@/app/(app)/(agent)/_hooks/use-integrations';
import { AddEnvironmentForm } from './add-environment-form';

import type { FC } from 'react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AddEnvironmentDialog: FC<Props> = ({ open, onOpenChange }) => {
  const { agentId } = useParams<{ agentId: string }>();
  const { data: integrationsData } = useIntegrations();

  const retellIntegrations = integrationsData.data.filter((i) => i.provider === 'retell');
  const hasIntegrations = retellIntegrations.length > 0;

  const close = () => onOpenChange(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-w-lg flex flex-col max-h-[90vh] p-6 gap-4">
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-lg leading-none font-semibold">Add environment</DialogTitle>
        </DialogHeader>

        {!hasIntegrations ? (
          <NoIntegrationsState onCancel={close} />
        ) : (
          open && (
            <AddEnvironmentForm
              agentId={agentId}
              integrations={retellIntegrations}
              onCancel={close}
              onSuccess={close}
            />
          )
        )}
      </DialogContent>
    </Dialog>
  );
};

const NoIntegrationsState: FC<{ onCancel: () => void }> = ({ onCancel }) => (
  <div className="space-y-4">
    <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
      <AlertTriangle className="w-4 h-4 shrink-0 text-yellow-500 mt-0.5" />
      <p className="text-sm text-yellow-600 dark:text-yellow-400">
        No Retell integrations found. Add one before creating an environment.
      </p>
    </div>
    <div className="flex justify-end gap-2 pt-1">
      <Button type="button" variant="outline" size="sm" onClick={onCancel}>
        Cancel
      </Button>
      <Button asChild size="sm">
        <Link href="/integrations">Go to Integrations</Link>
      </Button>
    </div>
  </div>
);
