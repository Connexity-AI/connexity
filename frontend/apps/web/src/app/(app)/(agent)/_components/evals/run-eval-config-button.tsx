'use client';

import { useRouter } from 'next/navigation';
import { Play } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import { useCreateRun } from '@/app/(app)/(agent)/_hooks/use-create-run';
import { UrlGenerator } from '@/common/url-generator/url-generator';

interface RunEvalConfigButtonProps {
  agentId: string;
  evalConfigId: string;
  label?: string;
  /** "row" = compact inline row action, "primary" = standard primary button */
  variant?: 'row' | 'primary';
  className?: string;
}

export function RunEvalConfigButton({
  agentId,
  evalConfigId,
  label = 'Run',
  variant = 'primary',
  className,
}: RunEvalConfigButtonProps) {
  const router = useRouter();
  const { mutateAsync, isPending } = useCreateRun(agentId);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await mutateAsync({
        body: { agent_id: agentId, eval_config_id: evalConfigId },
        autoExecute: true,
      });
      router.push(UrlGenerator.agentEvalsRuns(agentId));
    } catch (err) {
      console.error('Failed to start run', err);
    }
  };

  if (variant === 'row') {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleClick}
        disabled={isPending}
        className={cn(
          'h-auto gap-1 rounded border-border bg-foreground/10 px-2 py-1 text-[11px] font-normal text-foreground hover:bg-foreground/20 hover:text-foreground disabled:opacity-60 [&_svg]:size-3',
          className
        )}
      >
        <Play />
        {isPending ? 'Starting…' : label}
      </Button>
    );
  }

  return (
    <Button
      type="button"
      size="sm"
      onClick={handleClick}
      disabled={isPending}
      className={cn('h-8 gap-1.5 text-xs', className)}
    >
      <Play className="h-3.5 w-3.5" />
      {isPending ? 'Starting…' : label}
    </Button>
  );
}
