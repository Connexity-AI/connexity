export const waitMs = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
