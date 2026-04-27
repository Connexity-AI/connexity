'use client';

import { useState } from 'react';

import { useQueryClient } from '@tanstack/react-query';
import { Plug } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { integrationKeys } from '@/constants/query-keys';

import { AddIntegrationDialog } from '@/app/(app)/integrations/_components/add-integration-dialog';
import { IntegrationCard } from '@/app/(app)/integrations/_components/integration-card';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  initialData: IntegrationPublic[];
}

export const IntegrationsClient: FC<Props> = ({ initialData }) => {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const [integrations, setIntegrations] = useState<IntegrationPublic[]>(initialData);

  const handleAdded = (integration: IntegrationPublic) => {
    setIntegrations((prev) => [integration, ...prev]);
    void queryClient.invalidateQueries({ queryKey: integrationKeys.all });
  };

  const handleDeleted = (id: string) => {
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
    void queryClient.invalidateQueries({ queryKey: integrationKeys.all });
  };

  return (
    <div className="flex flex-1 flex-col min-w-0 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Integrations</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Connect voice AI providers to your workspace.
          </p>
        </div>
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plug className="w-4 h-4 mr-2" />
          Add Integration
        </Button>
      </div>

      {integrations.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <Plug className="h-5 w-5 text-muted-foreground/50" />
          </div>
          <p className="text-sm text-muted-foreground">No integrations yet</p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            Add your first integration to get started.
          </p>
        </div>
      ) : (
        <div className="max-w-4xl space-y-8">
          {Object.entries(
            integrations.reduce<Record<string, IntegrationPublic[]>>((acc, i) => {
              (acc[i.provider] ??= []).push(i);
              return acc;
            }, {}),
          ).map(([provider, items]) => (
            <div key={provider}>
              <h2 className="text-xs text-muted-foreground uppercase tracking-wider mb-3">
                {provider.charAt(0).toUpperCase() + provider.slice(1)}
              </h2>
              <div className="space-y-3">
                {items.map((integration) => (
                  <IntegrationCard
                    key={integration.id}
                    integration={integration}
                    onDeleted={handleDeleted}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <AddIntegrationDialog open={open} onOpenChange={setOpen} onAdded={handleAdded} />
    </div>
  );
};
