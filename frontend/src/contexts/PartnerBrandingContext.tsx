'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { validateAffiliationCode } from '@/lib/api';
import {
  type AffiliationBranding,
  affiliationFromApiResponse,
  clearStoredAffiliation,
  loadStoredAffiliation,
  normalizeAffiliationCode,
  readAffiliationCodeFromSearch,
  saveStoredAffiliation,
} from '@/lib/partnerBranding';

interface PartnerBrandingContextType {
  affiliation: AffiliationBranding | null;
  isLoading: boolean;
  error: string | null;
  applyCode: (rawCode: string) => Promise<AffiliationBranding>;
  clearAffiliation: () => void;
  hasCoBrand: boolean;
}

const PartnerBrandingContext = createContext<PartnerBrandingContextType | undefined>(undefined);

export function PartnerBrandingProvider({ children }: { children: React.ReactNode }) {
  const [affiliation, setAffiliation] = useState<AffiliationBranding | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applyCode = useCallback(async (rawCode: string) => {
    const code = normalizeAffiliationCode(rawCode);
    if (!code) throw new Error('Enter an affiliation code');
    setError(null);
    setIsLoading(true);
    try {
      const data = await validateAffiliationCode(code);
      const branding = affiliationFromApiResponse(data as unknown as Record<string, unknown>);
      saveStoredAffiliation(branding);
      setAffiliation(branding);
      return branding;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Invalid code';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearAffiliation = useCallback(() => {
    clearStoredAffiliation();
    setAffiliation(null);
    setError(null);
  }, []);

  useEffect(() => {
    async function init() {
      const stored = loadStoredAffiliation();
      if (stored) {
        setAffiliation(stored);
        setIsLoading(false);
        return;
      }

      const fromUrl = readAffiliationCodeFromSearch(window.location.search);
      if (fromUrl) {
        try {
          await applyCode(fromUrl);
        } catch {
          /* invalid ref in URL */
        }
      }
      setIsLoading(false);
    }

    void init();
  }, [applyCode]);

  const value = useMemo(
    () => ({
      affiliation,
      isLoading,
      error,
      applyCode,
      clearAffiliation,
      hasCoBrand: !!affiliation,
    }),
    [affiliation, isLoading, error, applyCode, clearAffiliation]
  );

  return (
    <PartnerBrandingContext.Provider value={value}>
      {children}
    </PartnerBrandingContext.Provider>
  );
}

export function usePartnerBranding(): PartnerBrandingContextType {
  const ctx = useContext(PartnerBrandingContext);
  if (!ctx) {
    throw new Error('usePartnerBranding must be used within PartnerBrandingProvider');
  }
  return ctx;
}
