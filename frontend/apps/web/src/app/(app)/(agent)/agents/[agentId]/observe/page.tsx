import { ObserveContent } from '@/app/(app)/(agent)/_components/observe/observe-content';

interface AgentObservePageProps {
  params: Promise<{ agentId: string }>;
}

export default async function AgentObservePage({ params }: AgentObservePageProps) {
  const { agentId } = await params;
  return <ObserveContent agentId={agentId} />;
}
