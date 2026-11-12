'use client';

import { useEffect, useRef, useState } from 'react';

import type { FC } from 'react';

const COPIED_FOR_MS = 1800;

interface Props {
  command: string;
}

/** Step 1's setup instruction: the only one the app gives a person (design). */
export const ConnectCommand: FC<Props> = ({ command }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), COPIED_FOR_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      // No clipboard (an insecure origin, or permission refused): select the command
      // so the person can copy it themselves.
      const code = codeRef.current;
      const selection = window.getSelection();
      if (code && selection) {
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
  };

  return (
    <div className="ml-[30px] flex flex-col gap-2.5">
      <span className="text-pretty text-ink-secondary">
        Connect your AI assistant to Connexity. In Claude Code, run:
      </span>
      <div className="flex items-center gap-2 rounded-md border border-hairline bg-surface-0 py-1.5 pr-1.5 pl-3.5">
        <code
          ref={codeRef}
          className="min-w-0 flex-1 truncate font-mono text-label leading-5 text-ink"
        >
          {command}
        </code>
        <button
          type="button"
          onClick={copy}
          className="h-7 flex-none cursor-pointer rounded-sm border border-border-control px-2.5 text-label text-ink hover:bg-wash"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
};

export default ConnectCommand;
