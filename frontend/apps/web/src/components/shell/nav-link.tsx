'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@workspace/ui/lib/utils';

import type { Route } from 'next';
import type { FC, ReactNode } from 'react';

interface Props {
  title: string;
  url: Route;
  /**
   * The icon, already rendered by the server component. A component itself (a function)
   * cannot be passed to a client component; an element can.
   */
  icon: ReactNode;
  /** A muted count after the name; none when zero. */
  count?: number;
}

const base = (path: string) => (path.length > 1 ? path.replace(/\/+$/, '') : path);

export const NavLink: FC<Props> = ({ title, url, icon, count }) => {
  const pathname = base(usePathname());
  const target = base(url);
  const isActive = pathname === target || pathname.startsWith(`${target}/`);

  return (
    <Link
      href={url}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'flex h-9 items-center gap-3 rounded-md px-3 text-body no-underline',
        isActive ? 'bg-wash text-ink' : 'text-ink-secondary hover:bg-wash'
      )}
    >
      {icon}
      <span>{title}</span>
      {count ? (
        <span className="ml-auto text-label text-ink-muted">{count.toLocaleString()}</span>
      ) : null}
    </Link>
  );
};

export default NavLink;
