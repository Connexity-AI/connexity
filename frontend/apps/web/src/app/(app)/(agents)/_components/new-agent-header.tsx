'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import { createDraftAgent } from '@/actions/agents';
import { isSuccessApiResult } from '@/utils/api';
import { PlatformHeader } from '@/components/common/platform-header';

import type { AgentPublic } from '@/client/types.gen';

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
  const [isPending, setIsPending] = useState(false);

  const handleCreate = async () => {
    setIsPending(true);
    const result = await createDraftAgent();
    if (isSuccessApiResult(result)) {
      const agent = result.data as AgentPublic;
      router.push(UrlGenerator.agent(agent.id));
    }
    setIsPending(false);
  };

  return (
    <Button size="sm" onClick={handleCreate} disabled={isPending}>
      <Plus className="size-4" />
      {isPending ? 'Creating...' : 'Add Agent'}
    </Button>
  );
};
