'use client';

import { useState, useTransition } from 'react';

import { cn } from '@workspace/ui/lib/utils';

import { revokePersonalAccessTokenAction } from '@/actions/personal-access-tokens';
import { isErrorApiResult } from '@/utils/api';

import type { PersonalAccessTokenPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  tokens: PersonalAccessTokenPublic[];
  workspaceCount: number;
}

/**
 * Account › Assistant access (designs/screens/Connexity Account.dc.html, section 3).
 * Lists the person's personal access tokens; OAuth connections come with the Account
 * feature.
 */
export const AssistantAccess: FC<Props> = ({ tokens, workspaceCount }) => {
  const [revoked, setRevoked] = useState<Set<string>>(new Set());
  const [failed, setFailed] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const reach = `Reaches ${workspaceCount} workspace${workspaceCount === 1 ? '' : 's'}`;

  const revoke = (token: PersonalAccessTokenPublic) => {
    setFailed(null);
    startTransition(async () => {
      const result = await revokePersonalAccessTokenAction(token.id);
      if (isErrorApiResult(result)) {
        setFailed(token.id);
        return;
      }
      setRevoked((current) => new Set(current).add(token.id));
    });
  };

  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
      <div className="px-6 py-4 text-pretty text-ink-secondary">
        Anything your assistant does is recorded as done by your assistant on your behalf. An
        assistant reaches exactly the workspaces you can access.
      </div>
      {tokens.map((token) => {
        const gone = revoked.has(token.id);
        return (
          <div
            key={token.id}
            className="flex min-h-[52px] items-center justify-between gap-3 border-t border-hairline pr-4 pl-6"
          >
            <span className="flex flex-col">
              <span className={cn(gone ? 'text-ink-muted' : 'text-ink')}>{token.name}</span>
              <span className="text-label text-ink-muted">
                {gone ? 'No access' : failed === token.id ? 'Could not revoke. Try again.' : reach}
              </span>
            </span>
            {gone ? (
              <span className="text-label text-ink-muted">Revoked</span>
            ) : (
              <button
                type="button"
                disabled={isPending}
                onClick={() => revoke(token)}
                className="h-7 cursor-pointer rounded-sm px-2.5 text-label text-ink-secondary hover:bg-wash hover:text-ink disabled:cursor-default"
              >
                Revoke
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AssistantAccess;
