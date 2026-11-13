import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Brand } from '@/components/common/brand';
import { NAV_ITEMS } from '@/components/shell/nav-items';
import NavLink from '@/components/shell/nav-link';
import ProfileMenu from '@/components/shell/profile-menu';

import type { UserPublic, WorkspacePublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  user: UserPublic;
  workspaces: WorkspacePublic[];
}

/** Connexity Sidebar (designs/screens/Connexity Sidebar.dc.html). */
export const Sidebar: FC<Props> = ({ user, workspaces }) => (
  <aside className="sticky top-0 flex h-screen w-[220px] flex-none flex-col gap-6 border-r border-hairline bg-surface-1 px-3 py-4">
    <Link href={UrlGenerator.home()} className="px-2 no-underline">
      <Brand />
    </Link>

    {NAV_ITEMS.length > 0 && (
      <nav aria-label="Pages" className="flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ title, url, icon: Icon }) => (
          <NavLink
            key={url}
            title={title}
            url={url}
            icon={<Icon className="size-4 shrink-0" aria-hidden />}
          />
        ))}
      </nav>
    )}

    <div className="mt-auto flex flex-col gap-1 border-t border-hairline pt-3">
      <ProfileMenu name={user.full_name?.trim() || user.email} workspaces={workspaces} />
    </div>
  </aside>
);

export default Sidebar;
