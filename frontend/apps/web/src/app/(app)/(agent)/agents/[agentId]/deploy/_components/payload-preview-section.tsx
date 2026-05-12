'use client';

import { AlertTriangle, ChevronDown } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import { PayloadCopyButton } from './payload-copy-button';

interface PayloadPreviewSectionProps {
  showMissingPublishedVersionInfo: boolean;
  payloadOpen: boolean;
  onTogglePayloadOpen: () => void;
  payloadPreview: string;
  isPayloadPreviewLoading: boolean;
}

export function PayloadPreviewSection({
  showMissingPublishedVersionInfo,
  payloadOpen,
  onTogglePayloadOpen,
  payloadPreview,
  isPayloadPreviewLoading,
}: PayloadPreviewSectionProps) {
  if (showMissingPublishedVersionInfo) {
    return (
      <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border text-[11px] text-muted-foreground">
        <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
        No published agent version yet — publish your first version, then return here.
      </div>
    );
  }

  const previewText = isPayloadPreviewLoading ? 'Loading payload preview…' : payloadPreview;
  const payloadPreviewHeader = (
    <Button
      type="button"
      variant="ghost"
      onClick={onTogglePayloadOpen}
      className="w-full h-auto justify-between px-3 py-2.5 text-left hover:bg-accent/30 transition-colors"
    >
      <span className="text-[11px] text-muted-foreground">Payload preview</span>
      <ChevronDown
        className={cn(
          'w-3.5 h-3.5 text-muted-foreground transition-transform',
          payloadOpen && 'rotate-180'
        )}
      />
    </Button>
  );

  if (!payloadOpen) {
    return <div className="rounded-lg border border-border overflow-hidden">{payloadPreviewHeader}</div>;
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      {payloadPreviewHeader}
      <div className="px-3 pb-3 border-t border-border">
        <div className="rounded-md bg-muted/30 border border-border overflow-hidden mt-2 relative">
          <div className="absolute top-2 right-4">
            <PayloadCopyButton text={payloadPreview} />
          </div>
          <pre className="text-[10px] text-muted-foreground font-mono px-3 py-2.5 pr-10 overflow-auto max-h-44 leading-relaxed">
            {previewText}
          </pre>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5">
          Sent as <code className="text-foreground/70">POST</code> with{' '}
          <code className="text-foreground/70">Content-Type: application/json</code>
        </p>
      </div>
    </div>
  );
}
