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

  static agentEdit(agentId: string) {
    return `/agents/${agentId}/edit` as Route;
  }

  static agentEvals(agentId: string) {
    return `/agents/${agentId}/evals` as Route;
  }

  static agentEvalsTestCases(agentId: string) {
    return `/agents/${agentId}/evals/test-cases` as Route;
  }

  static agentEvalsConfigs(agentId: string) {
    return `/agents/${agentId}/evals/eval-configs` as Route;
  }

  static agentEvalsRuns(agentId: string) {
    return `/agents/${agentId}/evals/eval-runs` as Route;
  }

  static agentEvalsRunDetail(agentId: string, runId: string) {
    return `/agents/${agentId}/evals/eval-runs/${runId}` as Route;
  }

  static agentEvalsCreate(agentId: string) {
    return `/agents/${agentId}/evals/create-eval` as Route;
  }

  static agentEvalsConfigDetail(agentId: string, evalConfigId: string) {
    return `/agents/${agentId}/evals/eval-configs/${evalConfigId}` as Route;
  }

  static agentDeploy(agentId: string) {
    return `/agents/${agentId}/deploy` as Route;
  }

  static agentObserve(agentId: string) {
    return `/agents/${agentId}/observe` as Route;
  }

  static metrics({ options, values }: MetricsType = {}) {
    const route = '/metrics/' as Route;
    return createTypedLink(route, emptyParser, options)(values);
  }

  // ── Integrations ──

  static integrations() {
    return '/integrations' as Route;
  }

  // ── API ──

  static apiClientProxy() {
    return '/api/client-proxy/' as Route;
  }
}
