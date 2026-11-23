import { notFound } from 'next/navigation';

import { listWorkspaces } from '@/actions/workspaces';
import { MembersView } from '@/components/agency/members-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgenciesService } from '@/client/sdk.gen';

import type { FC } from 'react';

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The agency of the workspace the person has open. */
const AgencySettings: FC = async () => {
  const open = (await listWorkspaces()).find((w) => w.is_open);
  if (!open) notFound();
  const { data: agency } = await AgenciesService.readAgency({
    path: { agency_id: open.agency_id },
  });
  if (!agency) throw new Error('The agency could not be loaded.');

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <div className="flex min-h-10 flex-col justify-center">
        <h1 className="m-0 text-title font-medium text-ink">Agency settings</h1>
        <span className="text-label text-ink-secondary">
          {agency.name} · {plural(agency.workspaces.length, 'workspace', 'workspaces')}
        </span>
      </div>
      <div className="grid grid-cols-1 items-start gap-8 md:grid-cols-[176px_minmax(0,1fr)]">
        <nav aria-label="Agency sections" className="flex flex-col gap-0.5">
          <span
            aria-current="page"
            className="flex h-9 items-center rounded-md bg-wash px-3 text-ink"
          >
            Members
          </span>
        </nav>
        <MembersView agency={agency} />
      </div>
    </div>
  );
};

/**
 * Agency settings (designs/screens/Connexity Agency.dc.html). Only Members is built;
 * Billing comes with the billing features (CLAUDE.md rule 14).
 */
const AgencyPage: FC = () => (
  <ErrorBoundarySuspense fallback={null}>
    <AgencySettings />
  </ErrorBoundarySuspense>
);

export default AgencyPage;
