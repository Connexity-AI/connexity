import { Badge } from '@workspace/ui/components/ui/badge';
import { cn } from '@workspace/ui/lib/utils';

import { TestCaseStatus } from '@/client/types.gen';

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="pb-2 mb-3 text-[10px] uppercase tracking-widest text-muted-foreground border-b border-border">
      {children}
    </p>
  );
}

export function FieldLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-1 text-[11px] text-muted-foreground">{children}</p>;
}

const STATUS_BADGE_CLASS: Record<TestCaseStatus, string> = {
  [TestCaseStatus.ACTIVE]: 'bg-green-500/15 text-green-400',
  [TestCaseStatus.DRAFT]: 'bg-amber-500/15 text-amber-400',
  [TestCaseStatus.ARCHIVED]: 'bg-accent text-muted-foreground/50',
};

export function StatusBadge({ status }: { status: TestCaseStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        'rounded border-transparent px-1.5 py-0.5 text-[10px] font-normal capitalize',
        STATUS_BADGE_CLASS[status]
      )}
    >
      {status}
    </Badge>
  );
}
