import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { CircleMinus } from 'lucide-react';

import { Brand } from '@/components/common/brand';
import { NAV_ITEMS } from '@/components/shell/nav-items';
import NavLink from '@/components/shell/nav-link';
import ProfileMenu from '@/components/shell/profile-menu';
import ReadinessRing from '@/components/shell/readiness-ring';
import { WorkNavLink } from '@/components/shell/work-nav-link';

import type { UserPublic, WorkspacePublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  user: UserPublic;
  workspaces: WorkspacePublic[];
  /** Tasks waiting for the person, for the Work entry. */
  waitingWork?: number;
  /** Setup completeness; the ring shows until it is 100. */
  readiness?: number;
  /** Days the agency's money lasts, when that is less than about a week. */
  balanceLowDays?: number;
}

/** Connexity Sidebar (designs/screens/Connexity Sidebar.dc.html). */
export const Sidebar: FC<Props> = ({
  user,
  workspaces,
  waitingWork,
  readiness,
  balanceLowDays,
}) => (
  <aside className="sticky top-0 flex h-screen w-[220px] flex-none flex-col gap-6 border-r border-hairline bg-surface-1 px-3 py-4">
    <Link href={UrlGenerator.home()} className="px-2 no-underline">
      <Brand />
    </Link>

    {NAV_ITEMS.length > 0 && (
      <nav aria-label="Pages" className="flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ title, url, icon: Icon, counted }) =>
          counted === 'work' ? (
            <WorkNavLink
              key={url}
              title={title}
              url={url}
              icon={<Icon className="size-4 shrink-0" aria-hidden />}
              waiting={waitingWork}
            />
          ) : (
            <NavLink
              key={url}
              title={title}
              url={url}
              icon={<Icon className="size-4 shrink-0" aria-hidden />}
            />
          )
        )}
      </nav>
    )}

    <div className="mt-auto flex flex-col gap-1 border-t border-hairline pt-3">
      {readiness !== undefined && readiness < 100 && <ReadinessRing percent={readiness} />}
      {balanceLowDays !== undefined && (
        <Link
          href={UrlGenerator.agency('billing')}
          className="flex h-8 items-center gap-2.5 rounded-md px-3 text-label text-ink no-underline hover:bg-wash"
        >
          <CircleMinus className="size-4 flex-none text-ink-secondary" aria-hidden />
          <span className="tabular-nums">
            Balance low · {balanceLowDays === 1 ? '1 day left' : `${balanceLowDays} days left`}
          </span>
        </Link>
      )}
      <ProfileMenu name={user.full_name?.trim() || user.email} workspaces={workspaces} />
    </div>
  </aside>
);

export default Sidebar;
