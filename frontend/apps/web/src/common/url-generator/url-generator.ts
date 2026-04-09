import { createTypedLink } from '@/common/url-generator/typed-links';
import { agentsParser, emptyParser } from '@/common/url-generator/parsers';
import type { Route } from 'next';
import type {
  AgentsType,
  AuthType,
  DashboardType,
  MetricsType,
} from '@/common/url-generator/types';

export class UrlGenerator {
  static home() {
    return '/' as Route;
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

  static forgotPassword({ options, values }: AuthType = {}) {
    const route = '/forgot-password/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  // ── Dashboard ──

  static dashboard({ options, values }: DashboardType = {}) {
    const route = '/agents/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  static agents({ options, values }: AgentsType = {}) {
    const route = '/agents/' as Route;
    return createTypedLink(route, agentsParser, options)(values);
  }

  static agent(agentId: string) {
    return `/agents/${agentId}/` as Route;
  }

  static metrics({ options, values }: MetricsType = {}) {
    const route = '/metrics/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  // ── Error pages ──

  static notFound() {
    return '/404/' as Route;
  }

  static serverError() {
    return '/500/' as Route;
  }

  // ── Static ──

  static images() {
    return '/images/' as Route;
  }

  static favicons() {
    return '/images/favicons/' as Route;
  }

  // ── API ──

  static apiOgImages() {
    return '/api/v1/open-graph/' as Route;
  }

  static apiClientProxy() {
    return '/api/client-proxy/' as Route;
  }
}
