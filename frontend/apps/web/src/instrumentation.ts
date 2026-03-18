/** Runs only once on server start. */

/** Log loaded env vars. */
export const register = async () => {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { prettyPrintObject } = await import('@/utils/log');
    const { getPublicEnv } = await import('@/config/process-env');

    prettyPrintObject(getPublicEnv(), 'Runtime process.env');

    // Log full process.env (debug only)
    // prettyPrintObject(process.env, 'Runtime full process.env');
  }
};
