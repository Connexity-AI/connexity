'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@workspace/ui/lib/utils';

import type { NavItem } from '@/components/shell/nav-items';
import type { FC } from 'react';

interface Props {
  item: NavItem;
}

export const NavLink: FC<Props> = ({ item }) => {
  const pathname = usePathname();
  const isActive = pathname === item.url || pathname.startsWith(`${item.url}/`);
  const Icon = item.icon;

  return (
    <Link
      href={item.url}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'flex h-9 items-center gap-3 rounded-md px-3 text-body no-underline',
        isActive ? 'bg-wash text-ink' : 'text-ink-secondary hover:bg-wash'
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      <span>{item.title}</span>
    </Link>
  );
};

export default NavLink;
