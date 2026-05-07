'use client';

import { useState } from 'react';

import { CheckCheck, Copy } from 'lucide-react';

import type { FC } from 'react';

interface Props {
  text: string;
}

export const PayloadCopyButton: FC<Props> = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
      title="Copy payload"
      aria-label="Copy payload"
    >
      {copied ? <CheckCheck className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
};
