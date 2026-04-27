import { SheetTitle } from '@workspace/ui/components/ui/sheet';

import type { ReactNode } from 'react';

interface SrOnlySheetTitleProps {
  children: ReactNode;
}

export function SrOnlySheetTitle({ children }: SrOnlySheetTitleProps) {
  return <SheetTitle className="sr-only">{children}</SheetTitle>;
}
