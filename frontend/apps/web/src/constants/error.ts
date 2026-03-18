export const API_ERROR_MESSAGE = {
  /** Validation error / Bad request. */
  _400: 'Bad Request.',
  /** Authentication required / Invalid credentials. */
  _401: 'Unauthorized.',
  /** Access is forbidden / Insufficient permissions. */
  _403: 'Forbidden.',
  /** Resource not found. */
  _404: 'Not Found.',
  /** Internal server error / Unexpected failure. */
  _500: 'Something went wrong.',
} as const;

export const ENV_ERROR_TYPE = 'ENV_ERROR' as const;
