import { isErrorApiResult } from '@/utils/api';
import { API_ERROR_MESSAGE, ENV_ERROR_TYPE } from '@/constants/error';

import type { ApiResult } from '@/types/api';

export const getApiErrorMessage = (error: unknown): string => {
  // Default error message
  let errorMessage: string = API_ERROR_MESSAGE._500;

  const detail = (error as any)?.detail;

  // detail is array
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0].msg === 'string')
    errorMessage = detail[0].msg;

  // detail is string
  if (typeof detail === 'string') errorMessage = detail;

  return errorMessage;
};

export const throwIfApiError = (result: ApiResult): void => {
  const isError = isErrorApiResult(result);
  if (isError) throw new Error(getApiErrorMessage(result.error));
};

export class EnvError extends Error {
  type = ENV_ERROR_TYPE;

  constructor(message: string) {
    super(message);
    Object.setPrototypeOf(this, EnvError.prototype);
  }
}
