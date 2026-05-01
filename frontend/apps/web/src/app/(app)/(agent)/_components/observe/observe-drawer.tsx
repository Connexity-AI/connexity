'use client';

import { Sheet, SheetContent } from '@workspace/ui/components/ui/sheet';

import { CallPanel } from './call-panel';
import { CreateTestCaseAiPrompt } from './create-test-case-ai-prompt';
import { ObserveManualTestCasePanel } from './observe-manual-test-case-panel';
import { ObserveTestCasePanel } from './observe-test-case-panel';

import { SrOnlySheetTitle } from '@/components/common/sr-only-sheet-title';

import type { CallPublic, TestCasePublic } from '@/client/types.gen';

export type ObserveRightPanelMode = 'ai-prompt' | 'manual-create' | 'test-case';

function getDrawerTitle(hasCall: boolean, rightPanelMode: ObserveRightPanelMode | null) {
  if (hasCall) return 'Call transcript';
  if (rightPanelMode === 'test-case') return 'Test case detail';
  if (rightPanelMode === 'manual-create') return 'New test case';
  return 'Generate test case';
}

interface ObserveDrawerProps {
  agentId: string;
  call: CallPublic | null;
  testCase: TestCasePublic | null;
  rightPanelMode: ObserveRightPanelMode | null;
  onClose: () => void;
  onCloseRightPanel: () => void;
  onCreateTestCaseManual: (call: CallPublic) => void;
  onCreateTestCaseAi: (call: CallPublic) => void;
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
  onCreateTestCaseManual,
  onCreateTestCaseAi,
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
          <CallPanel
            call={call}
            onCreateTestCaseManual={showRightPanel ? undefined : onCreateTestCaseManual}
            onCreateTestCaseAi={showRightPanel ? undefined : onCreateTestCaseAi}
          />
        ) : null}

        {call && showRightPanel ? <div className="w-px shrink-0 bg-border" /> : null}

        {rightPanelMode === 'ai-prompt' && call ? (
          <CreateTestCaseAiPrompt
            agentId={agentId}
            call={call}
            onClose={onCloseRightPanel}
          />
        ) : null}

        {rightPanelMode === 'manual-create' ? (
          <ObserveManualTestCasePanel
            agentId={agentId}
            call={call}
            onClose={onCloseRightPanel}
            onOpenAiAssistant={call ? () => onCreateTestCaseAi(call) : undefined}
          />
        ) : null}

        {rightPanelMode === 'test-case' ? (
          <ObserveTestCasePanel
            key={testCase?.id ?? 'none'}
            agentId={agentId}
            testCase={testCase}
            onClose={onCloseRightPanel}
            onRequestDelete={onRequestDeleteTestCase}
            onOpenAiAssistant={call ? () => onCreateTestCaseAi(call) : undefined}
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
