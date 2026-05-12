import { Pencil, ShieldCheck, Trash2 } from 'lucide-react';

import { Platform } from '@/client/types.gen';
import type { EnvironmentPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  environment: EnvironmentPublic;
  hasGate: boolean;
  gateConfigDeleted: boolean;
  onEdit: (environment: EnvironmentPublic) => void;
  onDelete: () => void;
}

interface PlatformBadgeInfo {
  label: string;
  className: string;
}

function getPlatformBadgeInfo(platform: EnvironmentPublic['platform']): PlatformBadgeInfo {
  if (platform === Platform.WEBHOOK) {
    return {
      label: 'Webhook',
      className: 'text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400',
    };
  }
  if (platform === Platform.VAPI) {
    return {
      label: 'Vapi',
      className: 'text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400',
    };
  }
  if (platform === Platform.ELEVENLABS) {
    return {
      label: 'ElevenLabs',
      className: 'text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400',
    };
  }

  return {
    label: 'Retell',
    className: 'text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400',
  };
}

const GateBadge: FC = () => {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 inline-flex items-center gap-1">
      <ShieldCheck className="w-2.5 h-2.5" />
      Eval gate
    </span>
  );
};

const DeletedConfigBadge: FC = () => {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
      config deleted
    </span>
  );
};

const OptionalGateBadge: FC<{ hasGate: boolean }> = ({ hasGate }) => {
  if (!hasGate) {
    return null;
  }
  return <GateBadge />;
};

const OptionalDeletedConfigBadge: FC<{ gateConfigDeleted: boolean }> = ({ gateConfigDeleted }) => {
  if (!gateConfigDeleted) {
    return null;
  }
  return <DeletedConfigBadge />;
};

export const EnvironmentCardHeader: FC<Props> = ({
  environment,
  hasGate,
  gateConfigDeleted,
  onEdit,
  onDelete,
}) => {
  const platformBadge = getPlatformBadgeInfo(environment.platform);

  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-border">
      <div className="flex items-center gap-2.5">
        <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)] shrink-0" />
        <span className="text-sm text-foreground">{environment.name}</span>
        <span className={platformBadge.className}>{platformBadge.label}</span>
        <OptionalGateBadge hasGate={hasGate} />
        <OptionalDeletedConfigBadge gateConfigDeleted={gateConfigDeleted} />
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
