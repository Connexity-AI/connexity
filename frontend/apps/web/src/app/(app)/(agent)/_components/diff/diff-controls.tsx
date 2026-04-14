'use client';

import { useEffect, useRef, useState } from 'react';

import { ArrowRight } from 'lucide-react';

import {
  Select,
  SelectContent,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import { DiffVersionOptions } from '@/app/(app)/(agent)/_components/diff/diff-version-options';

import type { DiffVersionId } from '@/app/(app)/(agent)/_context/diff-context';
import type { AgentVersionPublic } from '@/client/types.gen';

interface DiffControlsProps {
  versions: AgentVersionPublic[];
  fromVersion: DiffVersionId;
  toVersion: DiffVersionId;
  onFromChange: (version: DiffVersionId) => void;
  onToChange: (version: DiffVersionId) => void;
  /**
   * Scrolling container the sticky bar lives inside. Used as the
   * IntersectionObserver root so the "stuck" animation fires the instant
   * the sentinel scrolls past the top of *this* container — not the
   * viewport, which may not be the actual scroll ancestor in layouts
   * that constrain the page to 100vh.
   */
  scrollRootRef?: React.RefObject<HTMLElement | null>;
}

function toSelectValue(versionId: DiffVersionId): string {
  return versionId === 'draft' ? 'draft' : String(versionId);
}

function fromSelectValue(selectValue: string): DiffVersionId {
  return selectValue === 'draft' ? 'draft' : Number(selectValue);
}

export function DiffControls({
  versions,
  fromVersion,
  toVersion,
  onFromChange,
  onToChange,
  scrollRootRef,
}: DiffControlsProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [isStuck, setIsStuck] = useState(false);

  useEffect(() => {
    const sentinelElement = sentinelRef.current;
    if (!sentinelElement) return;

    // Observe against the actual scroll container when provided, so the
    // "stuck" transition fires the moment the sentinel crosses the top edge
    // of that container. Without `root`, IntersectionObserver uses the
    // viewport, which produces the "animates too late / bar scrolls away"
    // bug when the real scroll happens inside a nested overflow-auto element.
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry) setIsStuck(!entry.isIntersecting);
      },
      {
        root: scrollRootRef?.current ?? null,
        threshold: 0,
        rootMargin: '0px 0px 0px 0px',
      }
    );

    observer.observe(sentinelElement);
    return () => observer.disconnect();
  }, [scrollRootRef]);

  const sortedVersions = [...versions]
    .filter((version) => version.version !== null)
    .sort(
      (firstVersion, secondVersion) => (secondVersion.version ?? 0) - (firstVersion.version ?? 0)
    );

  return (
    <>
      <div ref={sentinelRef} aria-hidden className="h-px" />
      <div
        className={cn(
          'sticky top-0 z-5 flex items-center gap-2 transition-[background-color,border-radius,margin,padding] duration-150',
          isStuck
            ? '-mx-6 px-6 py-2.5 bg-background/95 backdrop-blur border-b rounded-none mb-3'
            : 'mb-3 px-4 py-2.5 bg-muted/30 border rounded-md'
        )}
      >
        <span className="text-xs text-muted-foreground font-medium shrink-0">From</span>
        <Select
          value={toSelectValue(fromVersion)}
          onValueChange={(selectValue) => onFromChange(fromSelectValue(selectValue))}
        >
          <SelectTrigger className="h-8 w-45 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <DiffVersionOptions sortedVersions={sortedVersions} />
          </SelectContent>
        </Select>

        <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />

        <span className="text-xs text-muted-foreground font-medium shrink-0">To</span>
        <Select
          value={toSelectValue(toVersion)}
          onValueChange={(selectValue) => onToChange(fromSelectValue(selectValue))}
        >
          <SelectTrigger className="h-8 w-45 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <DiffVersionOptions sortedVersions={sortedVersions} />
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
