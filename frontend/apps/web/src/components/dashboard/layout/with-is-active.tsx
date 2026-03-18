'use client';

import React, { Children, cloneElement, Fragment, isValidElement } from 'react';
import { usePathname } from 'next/navigation';

import { removeTrailingSlash } from '@/utils/path';

import type { FC, ReactElement } from 'react';

interface Props {
  children: ReactElement<{ isActive?: boolean }>;
  url: string;
}

/**
 * Client component that passes isActive prop to children.
 * Server component can't call client component with render prop. (to pass pathname)
 * Not easy to get pathname in server component, requires setting header in middleware...
 */
const WithIsActive: FC<Props> = ({ children, url }) => {
  const pathname = usePathname();

  const trimmedPathname = removeTrailingSlash(pathname);
  const trimmedUrl = removeTrailingSlash(url);

  const isActive = trimmedPathname === trimmedUrl;

  if (isValidElement(children) && children.type !== Fragment) {
    return cloneElement(children, { isActive });
  }

  return (
    <>
      {Children.map(children, (child) => {
        if (!isValidElement(child)) return child;

        return cloneElement(child, { isActive });
      })}
    </>
  );
};

export default WithIsActive;
