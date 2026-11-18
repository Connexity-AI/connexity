import type { Metadata } from 'next';

export const METADATA: Metadata = {
  title: 'Connexity',
  description: 'Connexity: operations for a fleet of conversational AI agents',
  // The three-loop logo (designs/screens/assets/connexity-logo.png). The Apple icon sits
  // on the dark surface: iOS fills a transparent icon with black.
  icons: {
    icon: [
      { url: '/assets/images/logo-64.png', sizes: '64x64', type: 'image/png' },
      { url: '/assets/images/logo-32.png', sizes: '32x32', type: 'image/png' },
    ],
    shortcut: '/assets/images/logo-64.png',
    apple: { url: '/assets/images/apple-icon.png', sizes: '180x180', type: 'image/png' },
  },
};
