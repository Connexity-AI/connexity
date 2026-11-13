'use client';

import { useEffect, useRef, useState } from 'react';

import type { FC } from 'react';

const COPIED_FOR_MS = 1800;

interface Props {
  value: string;
}

/** A monospace value with a Copy button at its right end. */
export const CopyField: FC<Props> = ({ value }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), COPIED_FOR_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // No clipboard (an insecure origin, or permission refused): select the value so
      // the person can copy it themselves.
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
    <div className="flex items-center gap-2 rounded-md border border-hairline bg-surface-0 py-1.5 pr-1.5 pl-3.5">
      <code ref={codeRef} className="min-w-0 flex-1 truncate font-mono text-label leading-5 text-ink">
        {value}
      </code>
      <button
        type="button"
        onClick={copy}
        className="h-7 flex-none cursor-pointer rounded-sm border border-border-control px-2.5 text-label text-ink hover:bg-wash"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
};

export default CopyField;
