import Link from 'next/link';
import { notFound } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { cn } from '@workspace/ui/lib/utils';

import { listWorkspaces } from '@/actions/workspaces';
import { BillingView } from '@/components/agency/billing-view';
import { MembersView } from '@/components/agency/members-view';
import { WorkspacesView } from '@/components/agency/workspaces-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgenciesService, BillingService } from '@/client/sdk.gen';
import { getApiErrorMessage } from '@/utils/error';

import type { FC } from 'react';

type Section = 'members' | 'billing' | 'workspaces';
const SECTIONS = [
  { key: 'members', label: 'Members', href: UrlGenerator.agency() },
  { key: 'billing', label: 'Billing', href: UrlGenerator.agency('billing') },
  { key: 'workspaces', label: 'Workspaces', href: UrlGenerator.agency('workspaces') },
] as const;

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The agency of the workspace the person has open. */
const AgencySettings: FC<{ section: Section; justPaid: boolean }> = async ({
  section,
  justPaid,
}) => {
  const open = (await listWorkspaces()).find((w) => w.is_open);
  if (!open) notFound();
  const path = { agency_id: open.agency_id };
  const [{ data: agency }, { data: table }, billing] = await Promise.all([
    AgenciesService.readAgency({ path }),
    section === 'workspaces'
      ? AgenciesService.readWorkspaces({ path })
      : Promise.resolve({ data: undefined }),
    section === 'billing' ? BillingService.readBilling({ path }) : Promise.resolve(undefined),
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
          {SECTIONS.filter(({ key }) => key !== 'billing' || agency.billing).map(
            ({ key, label, href }) => (
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
            )
          )}
        </nav>
        {table ? (
          <WorkspacesView agencyId={agency.id} table={table} />
        ) : billing?.data ? (
          <BillingView agencyId={agency.id} billing={billing.data} justPaid={justPaid} />
        ) : billing ? (
          // Members are refused with the sentence that names the Admins.
          <span className="text-ink-secondary">{getApiErrorMessage(billing.error)}</span>
        ) : (
          <MembersView agency={agency} />
        )}
      </div>
    </div>
  );
};

interface PageProps {
  searchParams: Promise<{ section?: string; checkout?: string }>;
}

/**
 * Agency settings (designs/screens/Connexity Agency.dc.html): Members, Billing where
 * paying is set up, and Workspaces. Billing shows the subscription, card and billing
 * details; its balance, usage and invoices come with their own features (CLAUDE.md
 * rule 14).
 */
const AgencyPage: FC<PageProps> = async ({ searchParams }) => {
  const params = await searchParams;
  const section: Section =
    params.section === 'workspaces' || params.section === 'billing' ? params.section : 'members';
  return (
    <ErrorBoundarySuspense fallback={null}>
      <AgencySettings section={section} justPaid={params.checkout === 'done'} />
    </ErrorBoundarySuspense>
  );
};

export default AgencyPage;
