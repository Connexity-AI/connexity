import { Pencil, Trash2 } from 'lucide-react';

import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  onEdit: (environment: EnvironmentPublic) => void;
  onDelete: () => void;
}

export const EnvironmentCardHeader: FC<Props> = ({ environment, onEdit, onDelete }) => {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-border">
      <div className="flex items-center gap-2.5">
        <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)] shrink-0" />
        <span className="text-sm text-foreground">{environment.name}</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          className="text-muted-foreground/40 hover:text-foreground transition-colors cursor-pointer"
          title="Edit environment"
          onClick={() => onEdit(environment)}
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
        <button
          className="text-muted-foreground/40 hover:text-red-400 transition-colors cursor-pointer"
          title="Remove environment"
          onClick={onDelete}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
