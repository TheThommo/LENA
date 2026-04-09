'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { TenantConfig, DEFAULT_TENANT, getTenantConfig, applyTenantTheme } from '@/lib/tenant';

interface TenantContextType {
  tenant: TenantConfig;
  setTenant: (config: TenantConfig) => void;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [tenant, setTenantState] = useState<TenantConfig>(DEFAULT_TENANT);

  const setTenant = (config: TenantConfig) => {
    setTenantState(config);
    applyTenantTheme(config);
  };

  useEffect(() => {
    applyTenantTheme(tenant);
  }, [tenant]);

  return (
    <TenantContext.Provider value={{ tenant, setTenant }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant(): TenantContextType {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
}
