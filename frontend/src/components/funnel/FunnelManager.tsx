'use client';

import React from 'react';
import WelcomeCaptureModal, { type WelcomeCapturePayload } from './WelcomeCaptureModal';
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
  onCapture: (data: WelcomeCapturePayload) => Promise<void>;
  onRegister: () => void;
  onLogin: () => void;
}

export type FunnelStage = 'welcome' | 'search-limit' | 'none';

export default function FunnelManager({
  sessionState,
  onCapture,
  onRegister,
  onLogin,
}: FunnelManagerProps) {
  const getCurrentStage = (): FunnelStage => {
    // Authenticated users skip the entire funnel
    if (sessionState.isRegistered) return 'none';

    // First-time visitor: need name + email + disclaimer + data consent
    const firstTimeCaptured =
      !!sessionState.name &&
      !!sessionState.email &&
      !!sessionState.disclaimerAccepted;
    if (!firstTimeCaptured) return 'welcome';

    // After 5 free searches: require signup
    if (sessionState.searchCount >= 5) return 'search-limit';

    return 'none';
  };

  const currentStage = getCurrentStage();

  return (
    <>
      <WelcomeCaptureModal
        isOpen={currentStage === 'welcome'}
        onSubmit={onCapture}
        onLogin={onLogin}
        brandName={sessionState.brandName}
      />
      <SearchLimitModal
        isOpen={currentStage === 'search-limit'}
        onRegister={onRegister}
        onLogin={onLogin}
      />
    </>
  );
}
