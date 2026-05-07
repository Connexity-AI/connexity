import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { GatePills } from './gate-pills';

import type { useEnvironmentCard } from '../_hooks/use-environment-card';
import type { FC } from 'react';

type EnvironmentCardState = ReturnType<typeof useEnvironmentCard>;

interface Props {
  cardState: EnvironmentCardState;
  agentId: string;
}

interface VersionItemProps {
  version: number;
  title: string | null | undefined;
  latestPublished: number | null;
  currentVersion: number | null;
}

function getSelectedValue(selectedVersion: number | null): string {
  if (selectedVersion == null) {
    return '';
  }
  return String(selectedVersion);
}

function getVersionLabel({
  version,
  title,
  latestPublished,
  currentVersion,
}: VersionItemProps): string {
  let label = `v${version}`;

  if (title) {
    label = `${label} — ${title}`;
  }
  if (version === latestPublished) {
    label = `${label} (latest)`;
  }
  if (version === currentVersion) {
    label = `${label} · current`;
  }

  return label;
}

const SelectedVersionGatePills: FC<Props> = ({ cardState, agentId }) => {
  if (!cardState.hasGate) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 shrink-0">
      <GatePills run={cardState.selectedVersionRun} agentId={agentId} />
    </div>
  );
};

export const EnvironmentCardSelectedVersion: FC<Props> = ({ cardState, agentId }) => {
  return (
    <div className="px-5 py-3 border-b border-border">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">
            Selected Version
          </p>
          <Select
            value={getSelectedValue(cardState.selectedVersion)}
            onValueChange={cardState.selectVersion}
            disabled={cardState.selectDisabled}
          >
            <SelectTrigger className="h-8 text-xs max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {cardState.publishedVersions.map((versionRow) => (
                <SelectItem key={versionRow.version} value={String(versionRow.version)} className="text-xs">
                  {getVersionLabel({
                    version: versionRow.version,
                    title: versionRow.title,
                    latestPublished: cardState.latestPublished,
                    currentVersion: cardState.currentVersion,
                  })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <SelectedVersionGatePills cardState={cardState} agentId={agentId} />
      </div>
    </div>
  );
};
