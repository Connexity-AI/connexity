/**
 * Repeat definition from import { RequestResult } from '@/client/client/types.gen';
 * Lot cleaner intellisense than Omit and Pick.
 */
export type ApiResult<
  TData = unknown,
  TError = unknown,
  ThrowOnError extends boolean = boolean,
> = ThrowOnError extends true
  ? { data: TData }
  :
      | { data: TData; error: undefined }
      | { data: undefined; error: TError };

export interface ClientProxyRouteParam {
  params: Promise<{ path: string[] }>;
}
