import { Figtree, JetBrains_Mono } from 'next/font/google';

import { NuqsAdapter } from 'nuqs/adapters/next/app';
import { Toaster } from '@workspace/ui/components/ui/toaster';

import QueryProvider from '@/components/common/query-provider';
import ThemeProvider from '@/components/common/theme-provider';

import type React from 'react';

import '@workspace/ui/global.css';

import { METADATA } from '@/constants/metadata';
import { PublicEnv } from '@/config/process-env';

import type { Metadata } from 'next';
import type { FC, ReactNode } from 'react';

const fontSans = Figtree({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-figtree',
});

const fontMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains-mono',
});

export const metadata: Metadata = METADATA;

interface Props {
  children: ReactNode;
}

const RootLayout: FC<Props> = ({ children }) => (
  <html lang="en" suppressHydrationWarning>
    <body className={`${fontSans.variable} ${fontMono.variable}`}>
      <PublicEnv />

      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <NuqsAdapter>
          <QueryProvider>{children}</QueryProvider>
        </NuqsAdapter>

        <Toaster />
      </ThemeProvider>
    </body>
  </html>
);

export default RootLayout;
