'use client';

import React from 'react';
import SearchLimitModal from './SearchLimitModal';

interface SessionState {
  name?: string;
  email?: string;
  disclaimerAccepted?: boolean;
  disclaimerAcceptedAt?: string;
  searchCount: number;
  isRegistered?: boolean;
  brandName?: string;
}

interface FunnelManagerProps {
  sessionState: SessionState;
  onRegister: () => void;
  onLogin: () => void;
}

export type FunnelStage = 'search-limit' | 'none';

/**
 * Demo-mode funnel (2026-04-18):
 *  - Anon visitors are NOT blocked on landing. They type a query,
 *    LENA asks for a one-click disclaimer inline, then runs the search.
 *  - After exactly 1 anon search completes, the SearchLimitModal pushes
 *    signup (backed by the server-side IP+UA fingerprint so a refresh
 *    cannot bypass the cap).
 *  - Registered users skip the modal; their 5-per-day limit is enforced
 *    by the backend, which returns a guardrail message rendered inline.
 */
export default function FunnelManager({
  sessionState,
  onRegister,
  onLogin,
}: FunnelManagerProps) {
  const getCurrentStage = (): FunnelStage => {
    if (sessionState.isRegistered) return 'none';
    if (sessionState.searchCount >= 1) return 'search-limit';
    return 'none';
  };

  const currentStage = getCurrentStage();

  return (
    <SearchLimitModal
      isOpen={currentStage === 'search-limit'}
      onRegister={onRegister}
      onLogin={onLogin}
    />
  );
}
