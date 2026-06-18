'use client';

import React from 'react';
import { TenantProvider } from '@/contexts/TenantContext';
import { PartnerBrandingProvider } from '@/contexts/PartnerBrandingContext';
import { SessionProvider } from '@/contexts/SessionContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProjectsProvider } from '@/contexts/ProjectsContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <TenantProvider>
      <PartnerBrandingProvider>
        <SessionProvider>
          <AuthProvider>
            {/* ProjectsProvider depends on AuthProvider (reads token) */}
            <ProjectsProvider>{children}</ProjectsProvider>
          </AuthProvider>
        </SessionProvider>
      </PartnerBrandingProvider>
    </TenantProvider>
  );
}
