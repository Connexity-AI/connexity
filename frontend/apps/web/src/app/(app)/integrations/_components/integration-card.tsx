'use client';

import { useState } from 'react';

import { Trash2 } from 'lucide-react';

import { DeleteIntegrationDialog } from '@/app/(app)/integrations/_components/delete-integration-dialog';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

const PROVIDER_STYLES: Record<string, string> = {
  retell: 'bg-purple-500/10 text-purple-400',
  elevenlabs: 'bg-green-500/10 text-green-400',
};

interface Props {
  integration: IntegrationPublic;
}

export const IntegrationCard: FC<Props> = ({ integration }) => {
  const [deleteOpen, setDeleteOpen] = useState(false);

  const formattedDate = new Date(integration.created_at).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  const badgeClass =
    PROVIDER_STYLES[integration.provider.toLowerCase()] ?? 'bg-muted text-muted-foreground';

  return (
    <>
      <div className="group border border-border rounded-lg p-4 hover:border-primary/30 transition-colors">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className={`px-2 py-0.5 rounded text-[10px] font-medium ${badgeClass}`}>
                {integration.provider.charAt(0).toUpperCase() + integration.provider.slice(1)}
              </div>
            </div>
            <h3 className="text-sm text-foreground font-medium mb-2">{integration.name}</h3>
            <code className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">
              {integration.masked_api_key}
            </code>
            <p className="text-[10px] text-muted-foreground/50 mt-2">Added {formattedDate}</p>
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              className="h-8 w-8 flex cursor-pointer items-center justify-center rounded text-muted-foreground hover:text-red-400 hover:bg-accent transition-colors"
              title="Delete integration"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <DeleteIntegrationDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        integration={integration}
      />
    </>
  );
};
