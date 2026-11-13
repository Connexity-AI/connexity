'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import { createSetupPromptAction } from '@/actions/personal-access-tokens';
import { CopyField } from '@/components/readiness/copy-field';

import type { FC } from 'react';

const COPIED_FOR_MS = 2000;
/** While no assistant is connected, Readiness is reloaded this often so step 1 ticks. */
const REFRESH_EVERY_MS = 5000;

const TABS = [
  { id: 'code', label: 'Claude Code' },
  { id: 'web', label: 'Claude.ai or ChatGPT' },
] as const;

type Tab = (typeof TABS)[number]['id'];
type PromptState = 'idle' | 'copied' | 'error';

/**
 * Copy text that is still being fetched. A clipboard write must start inside the click,
 * and the prompt comes from the server, so the write is given a promise of the text
 * (Safari refuses a write that starts after an await). Falls back to a plain write.
 */
const copyFetched = async (fetchText: () => Promise<string | null>): Promise<boolean> => {
  const text = fetchText();
  try {
    if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
      const blob = text.then((value) => {
        if (value === null) throw new Error('No setup prompt');
        return new Blob([value], { type: 'text/plain' });
      });
      await navigator.clipboard.write([new ClipboardItem({ 'text/plain': blob })]);
      return true;
    }
    const value = await text;
    if (value === null) return false;
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
};

/** Reload the page's server data every few seconds while mounted and visible. */
const useRefreshWhileOpen = () => {
  const router = useRouter();
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') router.refresh();
    }, REFRESH_EVERY_MS);
    const onShow = () => {
      if (document.visibilityState === 'visible') router.refresh();
    };
    document.addEventListener('visibilitychange', onShow);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onShow);
    };
  }, [router]);
};

interface Props {
  mcpUrl: string;
}

/**
 * Readiness step 1 while no assistant is connected (designs/screens/Connexity
 * Onboarding.dc.html; 12-adjustments.md item 26).
 */
export const ConnectAssistant: FC<Props> = ({ mcpUrl }) => {
  const [tab, setTab] = useState<Tab>('code');
  const [prompt, setPrompt] = useState<PromptState>('idle');
  const [isCopying, setIsCopying] = useState(false);
  useRefreshWhileOpen();

  useEffect(() => {
    if (prompt !== 'copied') return;
    const timer = setTimeout(() => setPrompt('idle'), COPIED_FOR_MS);
    return () => clearTimeout(timer);
  }, [prompt]);

  const copyPrompt = async () => {
    setIsCopying(true);
    const copied = await copyFetched(() => createSetupPromptAction());
    setIsCopying(false);
    setPrompt(copied ? 'copied' : 'error');
  };

  return (
    <div className="ml-[30px] flex flex-col gap-3.5">
      <div role="tablist" className="flex gap-5">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={cn(
              'cursor-pointer border-0 border-b bg-transparent px-0 pb-1 text-label',
              tab === id ? 'border-ink text-ink' : 'border-transparent text-ink-secondary'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'code' && (
        <div role="tabpanel" className="flex flex-col items-start gap-2.5">
          <span className="text-pretty text-ink-secondary">
            Paste this into Claude Code, in the app or the terminal.
          </span>
          <Button
            type="button"
            onClick={copyPrompt}
            disabled={isCopying}
            className="h-9 min-w-[168px] px-4"
          >
            {prompt === 'copied' ? 'Copied' : 'Copy setup prompt'}
          </Button>
          {prompt === 'error' ? (
            <span role="alert" className="text-label text-pretty text-critical">
              Could not create the setup prompt. Try again.
            </span>
          ) : (
            <span className="text-label text-pretty text-ink-muted">
              Creates a personal access token for you. You can revoke it in{' '}
              <Link href={UrlGenerator.account()} className="text-ink-secondary">
                Account
              </Link>
              .
            </span>
          )}
        </div>
      )}

      {tab === 'web' && (
        <div role="tabpanel" className="flex flex-col gap-2.5">
          <span className="text-ink-secondary">Settings → Connectors → Add custom connector</span>
          <CopyField value={mcpUrl} />
          <span className="text-ink-secondary">then click Connect and sign in.</span>
        </div>
      )}
    </div>
  );
};

export default ConnectAssistant;
