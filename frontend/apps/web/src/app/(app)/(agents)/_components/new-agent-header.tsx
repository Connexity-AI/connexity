'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { useCreateDraftAgent } from '@/app/(app)/(agents)/_hooks/use-create-draft-agent';
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
  const { handleCreate, isPending } = useCreateDraftAgent();

  return (
    <Button size="sm" onClick={handleCreate} disabled={isPending}>
      <Plus className="size-4" />
      {isPending ? 'Creating...' : 'Add Agent'}
    </Button>
  );
};
