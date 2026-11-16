import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Bot, Inbox, ListChecks, ListTodo, Phone } from 'lucide-react';

import type { LucideIcon } from 'lucide-react';
import type { Route } from 'next';

export interface NavItem {
  title: string;
  url: Route;
  icon: LucideIcon;
  /**
   * Shows a count next to the name: what waits for the person on Work (warm), or open
   * questions on Action items (muted).
   */
  counted?: 'work' | 'actionItems';
}

/**
 * The sidebar's pages, in the decided order: Work first and the landing page, then
 * Dashboard, Incidents, Agents, Calls, Issues and Settings (Decided 2026-11-16,
 * docs-internal/work.md decision 19). Action items stays until its questions move to
 * Work (10.128).
 *
 * A page is added here by the feature that builds it, never before: nothing appears on
 * screen that does not work end to end (CLAUDE.md rule 14). Keep the decided order when
 * adding one.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { title: 'Work', url: UrlGenerator.work(), icon: ListChecks, counted: 'work' },
  {
    title: 'Action items',
    url: UrlGenerator.actionItems(),
    icon: ListTodo,
    counted: 'actionItems',
  },
  { title: 'Agents', url: UrlGenerator.agents(), icon: Bot },
  { title: 'Calls', url: UrlGenerator.calls(), icon: Phone },
  { title: 'Issues', url: UrlGenerator.issues(), icon: Inbox },
];
