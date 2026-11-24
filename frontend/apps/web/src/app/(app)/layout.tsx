import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { listWorkspaces } from '@/actions/workspaces';
import { BillingStripe } from '@/components/shell/billing-stripe';
import Sidebar from '@/components/shell/sidebar';
import { WorkspaceDeleted } from '@/components/shell/workspace-deleted';
import { BillingService, ReadinessService, UsersService, WorkService } from '@/client/sdk.gen';
import { AUTH_COOKIE } from '@/constants/auth';

import type { MoneyPublic, UserPublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

async function getAuthenticatedUser(): Promise<UserPublic | undefined> {
  try {
    const result = await UsersService.readUserMe();
    return result.data ?? undefined;
  } catch {
    return undefined;
  }
}

/** What waits for the person on Work, the same number as the page; none when unread. */
async function waitingWork(): Promise<number | undefined> {
  try {
    const result = await WorkService.readWorkCounts();
    return result.data?.waiting;
  } catch {
    return undefined;
  }
}

/** Setup completeness for the sidebar's ring; none when it cannot be read. */
async function readinessPercent(): Promise<number | undefined> {
  try {
    const result = await ReadinessService.readReadiness();
    return result.data?.percent;
  } catch {
    return undefined;
  }
}

/**
 * The workspace the session was opened in, read from the session cookie for display
 * only: the server checks the session itself on every request.
 */
async function sessionWorkspaceId(): Promise<string | undefined> {
  const token = (await cookies()).get(AUTH_COOKIE)?.value;
  try {
    const payload: unknown = JSON.parse(
      Buffer.from(token?.split('.')[1] ?? '', 'base64url').toString('utf8')
    );
    const cid = (payload as { cid?: unknown } | null)?.cid;
    return typeof cid === 'string' ? cid : undefined;
  } catch {
    return undefined;
  }
}

/** What the agency has left; none where paying is not set up or it cannot be read. */
async function agencyMoney(agencyId: string | undefined): Promise<MoneyPublic | undefined> {
  if (!agencyId) return undefined;
  try {
    const result = await BillingService.readStatus({ path: { agency_id: agencyId } });
    return result.data ?? undefined;
  } catch {
    return undefined;
  }
}

interface Props {
  children: ReactNode;
}

/** The app shell: the sidebar and the page frame beside it. */
const AppLayout: FC<Props> = async ({ children }) => {
  const currentUser = await getAuthenticatedUser();

  if (!currentUser) redirect(UrlGenerator.login());

  const workspaces = await listWorkspaces();

  // A session stays valid after its workspace is deleted while the person reaches
  // another one. That workspace is no longer in their list: say so, once, in full.
  const openedIn = await sessionWorkspaceId();
  const another = workspaces.find((w) => w.is_open) ?? workspaces[0];
  if (openedIn && another && !workspaces.some((w) => w.id === openedIn))
    return <WorkspaceDeleted workspace={{ id: another.id, name: another.name }} />;
  const [waiting, readiness, money] = await Promise.all([
    waitingWork(),
    readinessPercent(),
    agencyMoney(another?.agency_id),
  ]);

  return (
    <div className="flex min-h-screen w-full bg-surface-0">
      <Sidebar
        user={currentUser}
        workspaces={workspaces}
        waitingWork={waiting}
        readiness={readiness}
        balanceLowDays={money?.state === 'low' ? (money.days_left ?? undefined) : undefined}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {money && <BillingStripe money={money} />}
        <main className="min-w-0 flex-1 px-8 pt-6 pb-12">{children}</main>
      </div>
    </div>
  );
};

export default AppLayout;
