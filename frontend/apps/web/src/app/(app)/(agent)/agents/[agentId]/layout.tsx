import { AgentEditHeader } from '@/app/(app)/(agent)/_components/header/agent-edit-header';
import { AgentEditFormProvider } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { AiSuggestionProvider } from '@/app/(app)/(agent)/_context/ai-suggestion-context';
import { DiffProvider } from '@/app/(app)/(agent)/_context/diff-context';
import { SuggestFixesProvider } from '@/app/(app)/(agent)/_context/suggest-fixes-context';
import { VersionsProvider } from '@/app/(app)/(agent)/_context/versions-context';

import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  params: Promise<{ agentId: string }>;
}

export default async function AgentLayout({ children, params }: Props) {
  const { agentId } = await params;

  return (
    <VersionsProvider>
      <DiffProvider>
        <AgentEditFormProvider agentId={agentId}>
          <AiSuggestionProvider>
            <SuggestFixesProvider>
              <AgentEditHeader />
              {children}
            </SuggestFixesProvider>
          </AiSuggestionProvider>
        </AgentEditFormProvider>
      </DiffProvider>
    </VersionsProvider>
  );
}
