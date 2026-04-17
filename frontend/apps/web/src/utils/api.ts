import type { ErrorResponse } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const isErrorApiResult = <TError = ErrorResponse>(
  result: ApiResult<unknown, TError>,
): result is { data: undefined; error: TError } =>
  'error' in result && result.error !== undefined;

/** Either doesn't have key or it's undefined. Must initialize to null.*/
export const isSuccessApiResult = <TData>(
  result: ApiResult<TData>,
): result is { data: TData; error: undefined } =>
  'data' in result && result.data !== undefined;
