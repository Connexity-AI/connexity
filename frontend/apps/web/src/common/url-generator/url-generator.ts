import { createTypedLink } from '@/common/url-generator/typed-links';
import { emptyParser } from '@/common/url-generator/parsers';
import type { Route } from 'next';
import type { AuthType } from '@/common/url-generator/types';

export class UrlGenerator {
  static home() {
    return '/' as Route;
  }

  static calls() {
    return '/calls/' as Route;
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
