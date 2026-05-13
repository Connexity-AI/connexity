export function isPresentUserFacingFormMessage(message: unknown): message is string {
  if (typeof message !== 'string') {
    return false;
  }

  const trimmed = message.trim();
  if (trimmed.length === 0) {
    return false;
  }

  if (trimmed.toLowerCase() === 'undefined') {
    return false;
  }

  return true;
}

export function resolveCustomUrlTestStatusMessage(message: unknown): string {
  if (isPresentUserFacingFormMessage(message)) {
    return message;
  }

  return 'Failed to test URL. Please verify the endpoint is reachable.';
}
