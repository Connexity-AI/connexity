'use client';

import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { useCreateDraftAgent } from '@/app/(app)/(agents)/_hooks/use-create-draft-agent';
import { isSuccessApiResult } from '@/utils/api';
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
  const router = useRouter();
  const { mutate, isPending } = useCreateDraftAgent();

  const handleCreate = () => {
    mutate(undefined, {
      onSuccess: (result) => {
        if (!isSuccessApiResult(result)) return;
        router.push(UrlGenerator.agentEdit(result.data.id));
      },
    });
  };

  return (
    <Button size="sm" onClick={handleCreate} disabled={isPending}>
      <Plus className="size-4" />
      {isPending ? 'Creating...' : 'Add Agent'}
    </Button>
  );
};
