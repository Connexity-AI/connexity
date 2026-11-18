'use client';

import { useEffect, useState } from 'react';

import {
  ChevronRight,
  Eye,
  Hand,
  Pencil,
  Phone,
  Plug,
  SquareTerminal,
  Terminal,
  User,
  X,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { Brand } from '@/components/common/brand';

import type { OnboardingStepPublic } from '@/client/types.gen';
import type { McpManifest, McpManifestGuide, McpManifestTool } from '@/schemas/mcp-manifest';
import type { FC, ReactNode } from 'react';

const EFFECT_ICON = {
  reads: Eye,
  writes: Pencil,
  reads_platform: Plug,
  talks_to_agent: Phone,
} as const;

const Card: FC<{ className?: string; children: ReactNode }> = ({ className, children }) => (
  <div className={cn('rounded-xl border border-hairline bg-surface-1', className)}>{children}</div>
);

const EffectChip: FC<{ effect: McpManifestTool['effect']; label: string }> = ({
  effect,
  label,
}) => {
  const Icon = EFFECT_ICON[effect];
  return (
    <span className="inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-md bg-unchecked-bg px-2 text-label font-medium text-ink-secondary shadow-[inset_0_0_0_1px_var(--color-hairline)]">
      <Icon className="size-3.5" aria-hidden />
      {label}
    </span>
  );
};

const DecisionChip: FC = () => (
  <span className="inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-md bg-warning-bg px-2 text-label font-medium text-warning">
    <Hand className="size-3.5" aria-hidden />
    Your decision
  </span>
);

/** `code` and **bold** inside a line of a guide. */
const inline = (text: string): ReactNode[] =>
  text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`'))
      return (
        <code key={index} className="font-mono text-label text-ink">
          {part.slice(1, -1)}
        </code>
      );
    if (part.startsWith('**') && part.endsWith('**'))
      return (
        <strong key={index} className="font-medium text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    return part;
  });

type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'item'; marker: string; text: string };

/** A guide's markdown as headings, paragraphs and list items: all the guides use. */
const blocks = (markdown: string): Block[] => {
  const out: Block[] = [];
  // A blank line ends a paragraph or a list item; the next line starts a new block.
  let open = false;
  for (const raw of markdown.split('\n')) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      open = false;
      continue;
    }
    const heading = /^#{1,6}\s+(.*)$/.exec(line);
    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    const numbered = /^\s*(\d+)\.\s+(.*)$/.exec(line);
    const last = out[out.length - 1];
    if (heading) {
      out.push({ kind: 'heading', text: heading[1] ?? '' });
      open = false;
      continue;
    }
    if (bullet) out.push({ kind: 'item', marker: '•', text: bullet[1] ?? '' });
    else if (numbered)
      out.push({ kind: 'item', marker: `${numbered[1]}.`, text: numbered[2] ?? '' });
    else if (open && last && last.kind !== 'heading') last.text = `${last.text} ${line.trim()}`;
    else out.push({ kind: 'paragraph', text: line.trim() });
    open = true;
  }
  return out;
};

const GuidePanel: FC<{ guide: McpManifestGuide; onClose: () => void }> = ({ guide, onClose }) => {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <aside
      aria-label="Guide"
      className="fixed inset-y-0 right-0 z-20 flex w-full max-w-[560px] flex-col border-l border-hairline bg-surface-1"
    >
      <div className="flex flex-none items-start gap-3 border-b border-hairline px-5 py-4">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="text-body font-medium text-ink">{guide.title}</span>
          <code className="break-all font-mono text-label text-ink-muted">{guide.uri}</code>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="flex size-8 flex-none items-center justify-center rounded-lg text-ink-secondary hover:bg-wash hover:text-ink"
        >
          <X className="size-4" aria-hidden />
        </button>
      </div>
      <div className="flex flex-col gap-3 overflow-y-auto px-5 py-4 text-body text-ink-secondary">
        {blocks(guide.text).map((block, index) => {
          if (block.kind === 'heading')
            return (
              <h3 key={index} className="mt-2 text-body font-medium text-ink">
                {inline(block.text)}
              </h3>
            );
          if (block.kind === 'item')
            return (
              <div key={index} className="flex gap-2">
                <span className="flex-none text-ink-muted">{block.marker}</span>
                <span className="min-w-0 text-pretty">{inline(block.text)}</span>
              </div>
            );
          return (
            <p key={index} className="m-0 text-pretty">
              {inline(block.text)}
            </p>
          );
        })}
      </div>
    </aside>
  );
};

const ToolRow: FC<{
  tool: McpManifestTool;
  labels: Record<string, string>;
  last: boolean;
  onGuide: (uri: string) => void;
}> = ({ tool, labels, last, onGuide }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn(!last && 'border-b border-hairline')}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-left hover:bg-wash"
      >
        <ChevronRight
          className={cn(
            'size-4 flex-none text-ink-muted transition-transform',
            open && 'rotate-90'
          )}
          aria-hidden
        />
        <span className="w-[200px] flex-none font-mono text-label text-ink">{tool.name}</span>
        <span className="flex flex-none items-center gap-1.5">
          <EffectChip effect={tool.effect} label={labels[tool.effect] ?? tool.effect} />
          {tool.needs_yes && <DecisionChip />}
        </span>
        <span className="min-w-[200px] flex-1 text-body text-ink-secondary">
          {tool.line}
          {tool.only_when_asked && <span className="text-ink-muted"> Only when you ask.</span>}
        </span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 px-4 pb-4 pl-11">
          <span className="text-label text-ink-muted">Inputs</span>
          {tool.inputs.length ? (
            <div className="overflow-hidden rounded-lg border border-hairline bg-surface-0">
              {tool.inputs.map((input, index) => (
                <div
                  key={input.name}
                  className={cn(
                    'flex flex-wrap items-baseline gap-x-4 gap-y-1 px-3 py-2',
                    index > 0 && 'border-t border-hairline'
                  )}
                >
                  <span className="flex w-[184px] flex-none items-baseline gap-2">
                    <code className="font-mono text-label text-ink">{input.name}</code>
                    {input.required && <span className="text-label text-warning">required</span>}
                  </span>
                  <code className="w-[140px] flex-none break-words font-mono text-label text-ink-muted">
                    {input.type}
                  </code>
                  <span className="min-w-[200px] flex-1 text-label text-ink-secondary">
                    {input.description}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <span className="text-label text-ink-secondary">None.</span>
          )}
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-label text-ink-muted">Guide</span>
            <button
              type="button"
              onClick={() => onGuide(tool.guide)}
              className="break-all text-left font-mono text-label text-ink underline decoration-border-control underline-offset-[3px] hover:decoration-ink"
            >
              {tool.guide}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const CopyButton: FC<{ value: string; idle: string; className: string; children?: ReactNode }> = ({
  value,
  idle,
  className,
  children,
}) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
    >
      {children}
      {copied ? 'Copied' : idle}
    </button>
  );
};

/** An instruction's text: `tool` as code, [[guide]] as a link that opens the guide. */
const instructionParts = (text: string, onGuide: (uri: string) => void): ReactNode[] =>
  text.split(/(`[^`]+`|\[\[[a-z-]+\]\])/g).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`'))
      return (
        <code key={index} className="font-mono text-label font-medium text-ink">
          {part.slice(1, -1)}
        </code>
      );
    if (part.startsWith('[[') && part.endsWith(']]')) {
      const uri = `connexity://guides/${part.slice(2, -2)}`;
      return (
        <button
          key={index}
          type="button"
          onClick={() => onGuide(uri)}
          className="font-mono text-label text-ink underline decoration-border-control underline-offset-[3px] hover:decoration-ink"
        >
          {uri}
        </button>
      );
    }
    return part;
  });

const ActorChip: FC<{ who: OnboardingStepPublic['who'] }> = ({ who }) => {
  const Icon = who === 'person' ? User : SquareTerminal;
  return (
    <span className="inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-md bg-unchecked-bg px-2 text-label font-medium text-ink-secondary shadow-[inset_0_0_0_1px_var(--color-hairline)]">
      <Icon className="size-3.5" aria-hidden />
      {who === 'person' ? 'You' : 'Your assistant'}
    </span>
  );
};

const StepRow: FC<{
  step: OnboardingStepPublic;
  number: number;
  onGuide: (uri: string) => void;
}> = ({ step, number, onGuide }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn(number > 1 && 'border-t border-hairline', open && 'bg-surface-2')}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-start gap-x-3 gap-y-1.5 px-4 py-3 text-left hover:bg-wash"
      >
        <ChevronRight
          className={cn(
            'mt-[3px] size-4 flex-none text-ink-muted transition-transform',
            open && 'rotate-90'
          )}
          aria-hidden
        />
        <span className="w-5 flex-none text-body font-medium tabular-nums text-ink-muted">
          {number}
        </span>
        <span className="min-w-[120px] flex-1 text-body font-medium text-pretty text-ink sm:w-[220px] sm:flex-none">
          {step.title}
        </span>
        <span className="order-3 flex pl-[60px] sm:order-none sm:w-[136px] sm:flex-none sm:pl-0">
          <ActorChip who={step.who} />
        </span>
        <span className="order-2 w-full pl-[60px] text-body text-pretty text-ink-secondary sm:order-none sm:w-auto sm:min-w-[220px] sm:flex-1 sm:pl-0">
          {step.done_when}
        </span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 pr-4 pb-4 pl-[76px]">
          <span className="text-label text-ink-muted">Instructions for your assistant</span>
          <ol className="m-0 flex list-none flex-col gap-1.5 p-0">
            {step.instructions.map((text, index) => (
              <li
                key={index}
                className="grid grid-cols-[20px_minmax(0,1fr)] gap-1 text-body text-ink-secondary"
              >
                <span className="tabular-nums text-ink-muted">{index + 1}.</span>
                <span className="text-pretty [overflow-wrap:anywhere]">
                  {instructionParts(text, onGuide)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

const Unavailable: FC = () => (
  <Card className="p-6">
    <p className="m-0 text-body text-ink-secondary">
      The contract from the MCP server could not be read right now. Try again in a minute.
    </p>
  </Card>
);

/** The MCP contract page. Everything on it comes from the server's manifest. */
export const McpDocsView: FC<{
  manifest: McpManifest | null;
  onboarding: OnboardingStepPublic[];
}> = ({ manifest, onboarding }) => {
  const [guideUri, setGuideUri] = useState<string | null>(null);
  const guide = manifest?.guides.find((item) => item.uri === guideUri) ?? null;
  const labels = Object.fromEntries(
    (manifest?.effects ?? []).map((effect) => [effect.key, effect.label ?? effect.key])
  );
  const url = manifest?.server_url ?? null;

  return (
    <div className="min-h-screen w-full bg-surface-0 px-4 text-ink">
      <main className="mx-auto flex w-full max-w-[960px] flex-col gap-8 pt-10 pb-16">
        <Brand />
        {!manifest ? (
          <Unavailable />
        ) : (
          <>
            <Card className="flex flex-wrap items-end justify-between gap-6 p-6">
              <div className="flex min-w-0 flex-[1_1_340px] flex-col gap-2">
                <span className="font-mono text-label text-ink-muted">
                  MCP · {manifest.tool_count} tools · {manifest.guide_count} guides
                </span>
                <h1 className="m-0 text-title font-medium text-balance">
                  What your assistant can do in Connexity
                </h1>
                <p className="m-0 text-body text-pretty text-ink-secondary">
                  Connexity gives a workspace for your assistant to manage your voice agents
                </p>
              </div>
              {url && (
                <div className="flex min-w-0 flex-[0_1_340px] flex-col gap-2">
                  <span className="text-label text-ink-secondary">Server URL</span>
                  <div className="flex items-center gap-2 rounded-lg border border-hairline bg-surface-0 py-1.5 pr-1.5 pl-3">
                    <code className="min-w-0 flex-1 truncate font-mono text-label">{url}</code>
                    <CopyButton
                      value={url}
                      idle="Copy"
                      className="h-7 flex-none rounded-md border border-border-control px-2.5 text-label text-ink hover:bg-wash"
                    />
                  </div>
                  <CopyButton
                    value={`claude mcp add --transport http --scope user connexity ${url}`}
                    idle="Copy Claude Code command"
                    className="flex h-9 items-center justify-center gap-2 rounded-lg bg-accent-ink px-4 text-body font-medium text-on-accent hover:opacity-90"
                  >
                    <Terminal className="size-4" aria-hidden />
                  </CopyButton>
                </div>
              )}
            </Card>

            <section className="flex flex-col gap-3">
              <h2 className="m-0 text-body font-medium">What a tool may do</h2>
              <Card className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-x-6 gap-y-3.5 px-5 py-4">
                {manifest.effects.map((effect) => (
                  <div key={effect.key} className="flex flex-col items-start gap-1.5">
                    {effect.key === 'decision' ? (
                      <DecisionChip />
                    ) : (
                      <EffectChip
                        effect={effect.key as McpManifestTool['effect']}
                        label={effect.label ?? effect.key}
                      />
                    )}
                    <span className="text-label text-ink-secondary">{effect.text}</span>
                  </div>
                ))}
              </Card>
            </section>

            {onboarding.length > 0 && (
              <section className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <h2 className="m-0 text-body font-medium">Onboarding</h2>
                  <span className="text-label text-pretty text-ink-secondary">
                    The steps a new workspace goes through, in order. Your assistant does them with
                    you.
                  </span>
                </div>
                <Card className="overflow-hidden">
                  {onboarding.map((step, index) => (
                    <StepRow key={step.key} step={step} number={index + 1} onGuide={setGuideUri} />
                  ))}
                </Card>
              </section>
            )}

            {manifest.groups.map((group) => (
              <section key={group.key} className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <h2 className="m-0 text-body font-medium">{group.name}</h2>
                  <span className="text-label text-pretty text-ink-secondary">{group.purpose}</span>
                </div>
                <Card className="overflow-hidden">
                  {group.tools.map((tool, index) => (
                    <ToolRow
                      key={tool.name}
                      tool={tool}
                      labels={labels}
                      last={index === group.tools.length - 1}
                      onGuide={setGuideUri}
                    />
                  ))}
                </Card>
              </section>
            ))}

            <section className="flex flex-col gap-3">
              <h2 className="m-0 text-body font-medium">Guides</h2>
              <Card className="overflow-hidden">
                {manifest.guides.map((item, index) => (
                  <button
                    key={item.uri}
                    type="button"
                    onClick={() => setGuideUri(item.uri)}
                    className={cn(
                      'flex w-full flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3 text-left hover:bg-wash',
                      index > 0 && 'border-t border-hairline'
                    )}
                  >
                    <code className="w-[280px] flex-none font-mono text-label text-ink">
                      {item.uri}
                    </code>
                    <span className="min-w-[200px] flex-1 text-body text-ink-secondary">
                      {item.title}
                    </span>
                  </button>
                ))}
              </Card>
            </section>

            <div className="flex flex-wrap gap-x-3 gap-y-1 text-label text-ink-muted">
              <span>Generated from the live MCP server.</span>
              <code className="font-mono">connexity-mcp {manifest.version}</code>
            </div>
          </>
        )}
      </main>
      {guide && <GuidePanel guide={guide} onClose={() => setGuideUri(null)} />}
    </div>
  );
};
