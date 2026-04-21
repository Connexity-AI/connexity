'use client';

import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ArrowLeft } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import type { Route } from 'next';
import type { ChangeEvent, ReactNode } from 'react';

function Root({ children }: { children: ReactNode }) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
      {children}
    </div>
  );
}

function Leading({ children }: { children: ReactNode }) {
  return <div className="flex items-center gap-3">{children}</div>;
}

function Actions({ children }: { children: ReactNode }) {
  return <div className="flex items-center gap-2">{children}</div>;
}

interface BackLinkProps {
  agentId: string;
  href?: Route;
}

function BackLink({ agentId, href }: BackLinkProps) {
  const target = href ?? UrlGenerator.agentEvalsTestCases(agentId);

  return (
    <Link
      href={target}
      className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="h-3.5 w-3.5" />
      Back
    </Link>
  );
}

function Separator() {
  return <span className="text-muted-foreground/30">/</span>;
}

interface NameInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

function NameInput({
  value,
  onChange,
  placeholder = 'Untitled Eval Config',
  disabled = false,
}: NameInputProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value);
  return (
    <input
      value={value}
      onChange={handleChange}
      disabled={disabled}
      className="w-64 border-none bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/40 disabled:cursor-default disabled:text-muted-foreground"
      placeholder={placeholder}
    />
  );
}

interface CancelButtonProps {
  agentId: string;
  href?: Route;
  label?: string;
}

function CancelButton({ agentId, href, label = 'Cancel' }: CancelButtonProps) {
  const target = href ?? UrlGenerator.agentEvalsTestCases(agentId);

  return (
    <Button asChild variant="ghost" size="sm" className="h-8 text-xs">
      <Link href={target}>{label}</Link>
    </Button>
  );
}

export const CreateEvalTopbar = Object.assign(Root, {
  Leading,
  Actions,
  BackLink,
  Separator,
  NameInput,
  CancelButton,
});
