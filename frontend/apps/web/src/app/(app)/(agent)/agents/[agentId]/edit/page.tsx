import { VersionsDrawer } from '@/app/(app)/(agent)/_components/diff/versions-drawer';
import { AgentEditTabs } from '@/app/(app)/(agent)/_components/header/agent-edit-tabs';
import { PublishDialog } from '@/app/(app)/(agent)/_components/header/publish-dialog';
import { ReadOnlyBanner } from '@/app/(app)/(agent)/_components/header/read-only-banner';

export default function AgentEditPage() {
  return (
    <>
      <ReadOnlyBanner />

      <div className="flex-1 flex min-h-0">
        <AgentEditTabs />
      </div>

      <VersionsDrawer />
      <PublishDialog />
    </>
  );
}
