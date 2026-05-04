'use client';

import { Drawer, DrawerContent, DrawerTitle } from '@workspace/ui/components/ui/drawer';

import { MetricDetail } from './metric-detail';

import type { MetricDraft } from './metric-detail';
import type { MetricUpdatePatch } from './metric-types';

type MetricDetailDrawerProps = {
  // When non-null the drawer is open and its body shows the form.
  // Switching `source.id` remounts MetricDetail so internal form
  // state (name, description, …) resets between metrics.
  source: MetricDraft | null;
  saved: boolean;
  saving: boolean;
  onSave: (patch: MetricUpdatePatch, draft: MetricDraft) => void;
  onDelete: () => void;
  onClose: () => void;
};

// Right-side slide-in (vaul / shadcn Drawer) wrapping the metric
// edit form. Encapsulates direction, sizing, scale-background opt-out,
// the a11y-required hidden title, and ESC/overlay-click → onClose
// wiring so the page just passes data + callbacks.
export function MetricDetailDrawer({
  source,
  saved,
  saving,
  onSave,
  onDelete,
  onClose,
}: MetricDetailDrawerProps) {
  const open = source !== null;

  return (
    <Drawer
      direction="right"
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      shouldScaleBackground={false}
    >
      <DrawerContent className="data-[vaul-drawer-direction=right]:!w-[640px] data-[vaul-drawer-direction=right]:sm:!max-w-[640px] flex flex-col">
        <DrawerTitle className="sr-only">Metric details</DrawerTitle>

        {source && (
          <MetricDetail
            key={source.id ?? 'draft'}
            source={source}
            saved={saved}
            saving={saving}
            onSave={onSave}
            onDelete={onDelete}
            onClose={onClose}
          />
        )}
      </DrawerContent>
    </Drawer>
  );
}
