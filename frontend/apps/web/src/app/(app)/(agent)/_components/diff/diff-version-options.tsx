import { Badge } from '@workspace/ui/components/ui/badge';
import { SelectItem } from '@workspace/ui/components/ui/select';

import type { AgentVersionPublic } from '@/client/types.gen';

interface DiffVersionOptionsProps {
  sortedVersions: AgentVersionPublic[];
}

export function DiffVersionOptions({ sortedVersions }: DiffVersionOptionsProps) {
  return (
    <>
      <SelectItem value="draft">
        <div className="flex items-center gap-2">
          <span>Draft</span>
          <Badge
            variant="secondary"
            className="h-4 px-1.5 text-[10px] bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-0"
          >
            latest
          </Badge>
        </div>
      </SelectItem>
      {sortedVersions.map((version) => (
        <SelectItem key={version.id} value={String(version.version)}>
          V{version.version}
        </SelectItem>
      ))}
    </>
  );
}
