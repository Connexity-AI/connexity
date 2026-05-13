'use client';

import { useState } from 'react';

import { Plus } from 'lucide-react';

import { NewAgentModal } from '@/app/(app)/(agents)/_components/new-agent-modal';
import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { PlatformHeader } from '@/components/common/platform-header';

export const NewAgentHeader = () => {
  return <PlatformHeader className="px-6" leading={<Leading />} trailing={<Trailing />} />;
};

const Leading = () => {
  return (
    <div className="flex items-center gap-3">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-5" />
      <span className="text-sm font-medium">Agents</span>
    </div>
  );
};

const Trailing = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="size-4" />
        New agent
      </Button>
      <NewAgentModal open={open} onOpenChange={setOpen} />
    </>
  );
};
