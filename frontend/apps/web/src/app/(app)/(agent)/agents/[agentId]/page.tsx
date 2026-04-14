import { AgentChatbotSlot } from '@/app/(app)/(agent)/_components/agent-chatbot/agent-chatbot-slot';
import { VersionsDrawer } from '@/app/(app)/(agent)/_components/diff/versions-drawer';
import { AgentEditHeader } from '@/app/(app)/(agent)/_components/header/agent-edit-header';
import { AgentEditTabs } from '@/app/(app)/(agent)/_components/header/agent-edit-tabs';
import { PublishDialog } from '@/app/(app)/(agent)/_components/header/publish-dialog';
import { ReadOnlyBanner } from '@/app/(app)/(agent)/_components/header/read-only-banner';
import { AgentEditFormProvider } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { AiSuggestionProvider } from '@/app/(app)/(agent)/_context/ai-suggestion-context';
import { DiffProvider } from '@/app/(app)/(agent)/_context/diff-context';
import { VersionsProvider } from '@/app/(app)/(agent)/_context/versions-context';

interface Props {
  params: Promise<{ agentId: string }>;
}

export default async function AgentPage({ params }: Props) {
  const { agentId } = await params;

  return (
    <VersionsProvider>
      <DiffProvider>
        <AgentEditFormProvider agentId={agentId}>
          <AiSuggestionProvider>
            <AgentEditHeader />

            <ReadOnlyBanner />

            <div className="flex-1 flex min-h-0">
              <AgentChatbotSlot />

              <AgentEditTabs />
            </div>

            <VersionsDrawer />
            <PublishDialog />
          </AiSuggestionProvider>
        </AgentEditFormProvider>
      </DiffProvider>
    </VersionsProvider>
  );
}
