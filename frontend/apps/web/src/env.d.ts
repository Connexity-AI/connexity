declare namespace NodeJS {
  interface ProcessEnv {
    readonly NODE_ENV: 'development' | 'production' | 'test';
    readonly SITE_URL: string;
    readonly API_URL: string;
  }
}
