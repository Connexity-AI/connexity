export const getCreateIntegrationErrorMessage = (error: unknown): string => {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    return String(error.detail);
  }

  return 'Failed to add integration. Check your API key and try again.';
};
