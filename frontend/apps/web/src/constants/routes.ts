// Todo: handle trailing '/' in Next.js app

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login/',
  REGISTER: '/register/',
  FORGOT_PASSWORD: '/forgot-password/',
  DASHBOARD: '/dashboard/',
  SETTINGS: '/dashboard/settings/',
  _404: '/404/',
  _500: '/500/',
  STATIC: {
    IMAGES: '/images/',
    FAVICONS: '/images/favicons/',
  },
  /**
   * API_V1_STR = /api/v1
   *
   * MUST point to backend, must use absolute URL
   *
   * @example: `${process.env.API_URL}${GITHUB_LOGIN}`
   */
  API: {
    LOGIN_GITHUB: '/api/v1/login/github/',
    OG_IMAGES: '/api/v1/open-graph/',
    /** Next.js API proxy route */
    CLIENT_PROXY: '/api/client-proxy/',
  },
} as const;
