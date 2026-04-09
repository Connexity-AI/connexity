import { agentsParser, emptyParser } from '@/common/url-generator/parsers';
import {
  type CreateSerializerOptions,
  type inferParserType,
  type Nullable,
  type ParserMap,
} from 'nuqs/server';

export type TypedLinkProps<Parsers extends ParserMap> = {
  options?: CreateSerializerOptions<Parsers>;
  values?: Partial<Nullable<inferParserType<Parsers>>>;
};

export type BaseRouteType = TypedLinkProps<typeof emptyParser>;

// ── Auth ──
export type AuthType = BaseRouteType;

// ── Dashboard ──
export type DashboardType = BaseRouteType;
export type AgentsType = TypedLinkProps<typeof agentsParser>;
export type MetricsType = BaseRouteType;
