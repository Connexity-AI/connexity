import Link from 'next/link';
import { notFound } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { cn } from '@workspace/ui/lib/utils';

import { listWorkspaces } from '@/actions/workspaces';
import { MembersView } from '@/components/agency/members-view';
import { WorkspacesView } from '@/components/agency/workspaces-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgenciesService } from '@/client/sdk.gen';

import type { FC } from 'react';

type Section = 'members' | 'workspaces';
const SECTIONS = [
  { key: 'members', label: 'Members', href: UrlGenerator.agency() },
  { key: 'workspaces', label: 'Workspaces', href: UrlGenerator.agency('workspaces') },
] as const;

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The agency of the workspace the person has open. */
const AgencySettings: FC<{ section: Section }> = async ({ section }) => {
  const open = (await listWorkspaces()).find((w) => w.is_open);
  if (!open) notFound();
  const path = { agency_id: open.agency_id };
  const [{ data: agency }, { data: table }] = await Promise.all([
    AgenciesService.readAgency({ path }),
    section === 'workspaces'
      ? AgenciesService.readWorkspaces({ path })
      : Promise.resolve({ data: undefined }),
  ]);
  if (!agency) throw new Error('The agency could not be loaded.');
  if (section === 'workspaces' && !table) throw new Error('The workspaces could not be loaded.');

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
          {SECTIONS.map(({ key, label, href }) => (
            <Link
              key={key}
              href={href}
              aria-current={key === section ? 'page' : undefined}
              className={cn(
                'flex h-9 items-center rounded-md px-3 no-underline',
                key === section ? 'bg-wash text-ink' : 'text-ink-secondary hover:bg-wash'
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
        {table ? (
          <WorkspacesView agencyId={agency.id} table={table} />
        ) : (
          <MembersView agency={agency} />
        )}
      </div>
    </div>
  );
};

interface PageProps {
  searchParams: Promise<{ section?: string }>;
}

/**
 * Agency settings (designs/screens/Connexity Agency.dc.html). Members and Workspaces
 * are built; Billing comes with the billing features (CLAUDE.md rule 14).
 */
const AgencyPage: FC<PageProps> = async ({ searchParams }) => {
  const section: Section = (await searchParams).section === 'workspaces' ? 'workspaces' : 'members';
  return (
    <ErrorBoundarySuspense fallback={null}>
      <AgencySettings section={section} />
    </ErrorBoundarySuspense>
  );
};

export default AgencyPage;
