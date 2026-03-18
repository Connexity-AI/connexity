/**
 * Repeat definition from import { RequestResult } from '@/client/client/types.gen';
 * Lot cleaner intellisense than Omit and Pick.
 */
export type ApiResult<
  TData = unknown,
  TError = unknown,
  ThrowOnError extends boolean = boolean,
> = ThrowOnError extends true
  ? {
      data: TData extends Record<string, unknown> ? TData[keyof TData] : TData;
    }
  :
      | {
          data: TData extends Record<string, unknown> ? TData[keyof TData] : TData;
          error: undefined;
        }
      | {
          data: undefined;
          error: TError extends Record<string, unknown> ? TError[keyof TError] : TError;
        };

export interface ClientProxyRouteParam {
  params: Promise<{ path: string[] }>;
}
