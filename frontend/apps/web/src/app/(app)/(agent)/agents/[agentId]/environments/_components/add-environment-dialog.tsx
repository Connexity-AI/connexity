'use client';

import { useParams } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { platformLabel } from '@/app/(app)/(agents)/_components/new-agent-platform-labels';
import { useIntegrations } from '@/app/(app)/(agent)/_hooks/use-integrations';
import { subtitlePlatformForAddEnvironmentDialog } from '@/app/(app)/(agent)/agents/[agentId]/environments/_utils/subtitle-platform-for-add-environment-dialog';
import { AddEnvironmentForm } from './add-environment-form';

import type { FC } from 'react';
import { IntegrationProvider } from '@/client/types.gen';
import type { EnvironmentPublic } from '@/client/types.gen';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  environment: EnvironmentPublic | null;
}

export const AddEnvironmentDialog: FC<Props> = ({ open, onOpenChange, environment }) => {
  const { agentId } = useParams<{ agentId: string }>();
  const { data: agent } = useAgent(agentId);
  const { data: integrationsData } = useIntegrations();
  const platformIntegrations = integrationsData.data.filter(
    (integration) =>
      integration.provider === IntegrationProvider.RETELL ||
      integration.provider === IntegrationProvider.VAPI ||
      integration.provider === IntegrationProvider.ELEVENLABS
  );
  const title = environment === null ? 'Add environment' : 'Edit environment';
  const subtitlePlatform = subtitlePlatformForAddEnvironmentDialog(environment, agent);

  const close = () => onOpenChange(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-w-lg flex flex-col max-h-[90vh] p-6 gap-4">
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-lg leading-none font-semibold">{title}</DialogTitle>
          {subtitlePlatform !== null && (
            <p className="text-[11px] text-muted-foreground mt-1">
              Link this agent to its {platformLabel(subtitlePlatform)} account
            </p>
          )}
        </DialogHeader>

        {open && (
          <AddEnvironmentForm
            agentId={agentId}
            integrations={platformIntegrations}
            environment={environment}
            onCancel={close}
            onSuccess={close}
          />
        )}
      </DialogContent>
    </Dialog>
  );
};
