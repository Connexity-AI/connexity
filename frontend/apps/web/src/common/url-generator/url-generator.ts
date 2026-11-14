import { emptyParser } from '@/common/url-generator/parsers';
import { createTypedLink } from '@/common/url-generator/typed-links';

import type { AuthType } from '@/common/url-generator/types';
import type { Route } from 'next';

export class UrlGenerator {
  static home() {
    return '/' as Route;
  }

  static agents() {
    return '/agents/' as Route;
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

  static issue(id: string) {
    return `/issues/${id}/` as Route;
  }

  static issueCalls(id: string) {
    return `/calls/?issue=${id}` as Route;
  }

  static account() {
    return '/account/' as Route;
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

  // ── API ──

  static apiClientProxy() {
    return '/api/client-proxy/' as Route;
  }
}
