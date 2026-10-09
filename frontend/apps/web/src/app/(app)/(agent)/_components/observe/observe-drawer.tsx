'use client';

import { Sheet, SheetContent } from '@workspace/ui/components/ui/sheet';

import { SrOnlySheetTitle } from '@/components/common/sr-only-sheet-title';
import { CallPanel } from './call-panel';
import { ObserveTestCasePanel } from './observe-test-case-panel';

import type { CallPublic, TestCasePublic } from '@/client/types.gen';

export type ObserveRightPanelMode = 'test-case';

function getDrawerTitle(hasCall: boolean, rightPanelMode: ObserveRightPanelMode | null) {
  if (hasCall) return 'Call transcript';
  if (rightPanelMode === 'test-case') return 'Test case detail';
  return 'Test case';
}

interface ObserveDrawerProps {
  agentId: string;
  call: CallPublic | null;
  testCase: TestCasePublic | null;
  rightPanelMode: ObserveRightPanelMode | null;
  onClose: () => void;
  onCloseRightPanel: () => void;
  onRequestDeleteTestCase: (testCase: TestCasePublic) => void;
  batchPosition?: number;
  batchTotal?: number;
  onBatchPrev?: () => void;
  onBatchNext?: () => void;
}

export function ObserveDrawer({
  agentId,
  call,
  testCase,
  rightPanelMode,
  onClose,
  onCloseRightPanel,
  onRequestDeleteTestCase,
  batchPosition,
  batchTotal,
  onBatchPrev,
  onBatchNext,
}: ObserveDrawerProps) {
  const isOpen = !!call || !!testCase || !!rightPanelMode;
  const showRightPanel = !!rightPanelMode;
  const width = call && showRightPanel ? 900 : call ? 480 : 420;

  function handleOpenChange(open: boolean) {
    if (!open) {
      onClose();
      onCloseRightPanel();
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={handleOpenChange}>
      <SheetContent
        side="right"
        style={{ width, maxWidth: '100vw' }}
        className="flex flex-row gap-0 overflow-hidden border-l border-border bg-background p-0 transition-[width,max-width] duration-200 ease-out [&>button.absolute]:hidden"
      >
        <SrOnlySheetTitle>{getDrawerTitle(!!call, rightPanelMode)}</SrOnlySheetTitle>

        {call ? (
          <CallPanel key={call.id} agentId={agentId} call={call} />
        ) : null}

        {call && showRightPanel ? <div className="w-px shrink-0 bg-border" /> : null}

        {rightPanelMode === 'test-case' ? (
          <ObserveTestCasePanel
            key={testCase?.id ?? 'none'}
            agentId={agentId}
            testCase={testCase}
            onClose={onCloseRightPanel}
            onRequestDelete={onRequestDeleteTestCase}
            position={batchPosition}
            total={batchTotal}
            onPrev={onBatchPrev}
            onNext={onBatchNext}
          />
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
