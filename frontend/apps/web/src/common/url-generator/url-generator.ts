import { emptyParser } from '@/common/url-generator/parsers';
import { createTypedLink } from '@/common/url-generator/typed-links';

import type { AuthType } from '@/common/url-generator/types';
import type { Route } from 'next';

export class UrlGenerator {
  static home() {
    return '/' as Route;
  }

  /** Work; with an agent, its question cards open under its waiting row. */
  static work(answerAgentId?: string) {
    return (answerAgentId ? `/work/?answer=${answerAgentId}` : '/work/') as Route;
  }

  static agents() {
    return '/agents/' as Route;
  }

  static agent(id: string) {
    return `/agents/${id}/` as Route;
  }

  /** One tab of an agent's page, as Work's Done rows link. */
  static agentTab(id: string, tab: 'spec' | 'tests' | 'calls' | 'issues') {
    return `/agents/${id}/?tab=${tab}` as Route;
  }

  static calls() {
    return '/calls/' as Route;
  }

  static call(id: string, atSeconds?: number) {
    const at = atSeconds != null ? `?t=${Math.floor(atSeconds)}` : '';
    return `/calls/${id}/${at}` as Route;
  }

  static issues() {
    return '/issues/' as Route;
  }

  /** Issues of one area (a category key) over the same period and agent, as the
   * Dashboard's area rows link. */
  static issuesInArea(category: string, options?: { period?: string; agent?: string | null }) {
    const query = new URLSearchParams({ category });
    if (options?.period) query.set('period', options.period);
    if (options?.agent) query.set('agent', options.agent);
    return `/issues/?${query.toString()}` as Route;
  }

  /** One agent's open critical issues over a period (on one version when given), as the
   * Agents list and the agent Overview link their critical count. */
  static criticalIssues(agent: string, period?: string, version?: string | null) {
    const query = new URLSearchParams({ agent, severity: 'critical' });
    if (period && period !== '30d') query.set('period', period);
    if (version) query.set('version', version);
    return `/issues/?${query.toString()}` as Route;
  }

  /** The Dashboard, for all agents or one, over a period. */
  static dashboard(options?: { period?: string; agent?: string }) {
    const query = new URLSearchParams();
    if (options?.period && options.period !== '30d') query.set('period', options.period);
    if (options?.agent) query.set('agent', options.agent);
    const tail = query.toString();
    return (tail ? `/dashboard/?${tail}` : '/dashboard/') as Route;
  }

  static issue(id: string) {
    return `/issues/${id}/` as Route;
  }

  static issueCalls(id: string) {
    return `/calls/?issue=${id}` as Route;
  }

  static account() {
    return '/account/' as Route;
  }

  static agency(section?: 'workspaces') {
    return (section ? `/agency/?section=${section}` : '/agency/') as Route;
  }

  // ── Auth ──

  static login({ options, values }: AuthType = {}) {
    const route = '/login/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  static register({ options, values }: AuthType = {}) {
    const route = '/register/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  static invite(token: string) {
    return `/invite/${token}/` as Route;
  }

  static forgotPassword() {
    return '/forgot-password/' as Route;
  }

  // ── API ──

  static apiClientProxy() {
    return '/api/client-proxy/' as Route;
  }
}
