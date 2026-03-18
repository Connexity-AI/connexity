import type { HttpValidationError } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const isErrorApiResult = (
  result: ApiResult
): result is { data: undefined; error: HttpValidationError } =>
  'error' in result && result.error !== undefined;

/** Either doesn't have key or it's undefined. Must initialize to null.*/
export const isSuccessApiResult = (
  result: ApiResult
): result is { data: unknown; error: undefined } => 'data' in result && result.data !== undefined;
