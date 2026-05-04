'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { PlatformHeader } from '@/components/common/platform-header';

export const MetricsHeader = () => {
  return <PlatformHeader className="px-6" leading={<Leading />} trailing={<Trailing />} />;
};

const Leading = () => {
  return (
    <div className="flex items-center gap-3">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-5" />
      <span className="text-sm font-medium">Metrics</span>
    </div>
  );
};

// Pushes `?new=1`. The page (`MetricsPage`) listens for that param and
// opens the metric-draft drawer, then strips the param from the URL.
// Using a Link keeps this a server-friendly client component with no
// router/state plumbing back to the page.
const Trailing = () => {
  return (
    <Button asChild size="sm" className="gap-1.5 h-8">
      <Link href="?new=1" scroll={false}>
        <Plus className="size-4" />
        New metric
      </Link>
    </Button>
  );
};
