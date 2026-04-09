'use client';

import React from 'react';
import { TenantProvider } from '@/contexts/TenantContext';
import { SessionProvider } from '@/contexts/SessionContext';
import { AuthProvider } from '@/contexts/AuthContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <TenantProvider>
      <SessionProvider>
        <AuthProvider>{children}</AuthProvider>
      </SessionProvider>
    </TenantProvider>
  );
}
