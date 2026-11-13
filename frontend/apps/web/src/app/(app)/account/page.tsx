import { listWorkspaces } from '@/actions/workspaces';
import { AssistantAccess } from '@/components/account/assistant-access';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { TokensService } from '@/client/sdk.gen';

import type { FC } from 'react';

const AssistantAccessSection: FC = async () => {
  const [result, workspaces] = await Promise.all([
    TokensService.listPersonalAccessTokens(),
    listWorkspaces(),
  ]);
  if (!result.data) throw new Error('Assistant access could not be loaded.');

  return <AssistantAccess tokens={result.data.data} workspaceCount={workspaces.length} />;
};

/**
 * Personal settings (designs/screens/Connexity Account.dc.html). Only Assistant access
 * is built; the other sections come with the Account feature (CLAUDE.md rule 14).
 */
const AccountPage: FC = () => (
  <div className="flex max-w-[1120px] flex-col gap-6">
    <div className="flex min-h-10 items-center">
      <h1 className="m-0 text-title font-medium text-ink">Account</h1>
    </div>
    <div className="grid grid-cols-[176px_minmax(0,1fr)] items-start gap-8">
      <nav aria-label="Account sections" className="flex flex-col gap-0.5">
        <span
          aria-current="page"
          className="flex h-9 items-center rounded-md bg-wash px-3 text-ink"
        >
          Assistant access
        </span>
      </nav>
      <div className="flex max-w-[760px] min-w-0 flex-col gap-4">
        <ErrorBoundarySuspense fallback={null}>
          <AssistantAccessSection />
        </ErrorBoundarySuspense>
      </div>
    </div>
  </div>
);

export default AccountPage;
