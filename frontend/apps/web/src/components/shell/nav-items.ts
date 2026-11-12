import type { LucideIcon } from 'lucide-react';
import type { Route } from 'next';

export interface NavItem {
  title: string;
  url: Route;
  icon: LucideIcon;
}

/**
 * The sidebar's pages, in the decided order: Home, Incidents, Action items, Agents,
 * Calls, Roadmap, Issues, Settings (Decided 2026-11-12).
 *
 * A page is added here by the feature that builds it, never before: nothing appears on
 * screen that does not work end to end (CLAUDE.md rule 14). Keep the decided order when
 * adding one.
 */
export const NAV_ITEMS: readonly NavItem[] = [];
