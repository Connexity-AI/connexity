import Image from 'next/image';

import type { FC } from 'react';

/** The logo and "Connexity", at the top of the sidebar and the sign-in pages. */
export const Brand: FC = () => (
  <span className="flex h-8 items-center gap-2">
    <Image
      src="/connexity-logo.avif"
      alt=""
      width={22}
      height={22}
      className="flex-none rounded-sm"
      priority
    />
    <span className="text-body font-medium text-ink">Connexity</span>
  </span>
);

export default Brand;
