'use client';

import { useParams } from 'next/navigation';
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

  const close = () => onOpenChange(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-w-lg flex flex-col max-h-[90vh] p-6 gap-4">
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-lg leading-none font-semibold">Add environment</DialogTitle>
        </DialogHeader>

        {open && (
          <AddEnvironmentForm
            agentId={agentId}
            integrations={retellIntegrations}
            onCancel={close}
            onSuccess={close}
          />
        )}
      </DialogContent>
    </Dialog>
  );
};
