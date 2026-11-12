import type { FC, ReactNode } from 'react';

interface Props {
  title: string;
  /** Muted line under the title, such as source and freshness. */
  caption?: ReactNode;
  /** Right side, such as the period picker. */
  actions?: ReactNode;
}

/** The bar every page opens with (Connexity Design System, layout). */
export const PageBar: FC<Props> = ({ title, caption, actions }) => (
  <header className="flex min-h-10 items-center justify-between gap-4">
    <div className="flex min-w-0 flex-col">
      <h1 className="m-0 truncate text-title font-medium text-ink">{title}</h1>
      {caption && <p className="m-0 text-label text-ink-muted">{caption}</p>}
    </div>
    {actions && <div className="flex flex-none items-center gap-3">{actions}</div>}
  </header>
);

export default PageBar;
