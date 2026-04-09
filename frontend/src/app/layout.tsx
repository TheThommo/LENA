import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Providers } from '@/components/Providers';

export const metadata: Metadata = {
  title: 'LENA - Literature and Evidence Navigation Agent',
  description: 'AI-powered clinical research assistant with cross-reference validation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
