import { CheckCircle2, CircleOff, Clock, Loader2, XCircle } from 'lucide-react';

import { RunStatus } from '@/client/types.gen';
import { cn } from '@workspace/ui/lib/utils';

interface RunStatusIconProps {
  status: RunStatus;
  className?: string;
}

export function RunStatusIcon({ status, className }: RunStatusIconProps) {
  switch (status) {
    case RunStatus.COMPLETED:
      return <CheckCircle2 className={cn('h-3.5 w-3.5 text-green-400', className)} />;
    case RunStatus.RUNNING:
      return (
        <Loader2 className={cn('h-3.5 w-3.5 animate-spin text-blue-400', className)} />
      );
    case RunStatus.FAILED:
      return <XCircle className={cn('h-3.5 w-3.5 text-red-400', className)} />;
    case RunStatus.CANCELLED:
      return <CircleOff className={cn('h-3.5 w-3.5 text-muted-foreground', className)} />;
    case RunStatus.PENDING:
    default:
      return <Clock className={cn('h-3.5 w-3.5 text-muted-foreground', className)} />;
  }
}

export function runStatusLabel(status: RunStatus): string {
  switch (status) {
    case RunStatus.COMPLETED:
      return 'Completed';
    case RunStatus.RUNNING:
      return 'Running';
    case RunStatus.FAILED:
      return 'Failed';
    case RunStatus.CANCELLED:
      return 'Cancelled';
    case RunStatus.PENDING:
      return 'Pending';
    default:
      return String(status);
  }
}

export function runStatusBadgeClasses(status: RunStatus): string {
  switch (status) {
    case RunStatus.COMPLETED:
      return 'bg-green-500/15 text-green-400 border-green-500/25';
    case RunStatus.RUNNING:
      return 'bg-blue-500/15 text-blue-400 border-blue-500/25';
    case RunStatus.FAILED:
      return 'bg-red-500/15 text-red-400 border-red-500/25';
    case RunStatus.CANCELLED:
      return 'bg-muted/40 text-muted-foreground border-border';
    case RunStatus.PENDING:
    default:
      return 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25';
  }
}
