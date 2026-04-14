'use client';

import React from 'react';
import NameCaptureModal from './NameCaptureModal';
import DisclaimerModal from './DisclaimerModal';
import EmailCaptureModal, { type EmailCaptureData } from './EmailCaptureModal';
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
  onNameSubmit: (name: string) => void;
  onDisclaimerAccept: (timestamp: string) => void;
  onEmailSubmit: (data: EmailCaptureData) => void;
  onEmailSkip: () => void;
  onRegister: () => void;
  onLogin: () => void;
}

export type FunnelStage =
  | 'name'
  | 'disclaimer'
  | 'email'
  | 'search-limit'
  | 'none';

export default function FunnelManager({
  sessionState,
  onNameSubmit,
  onDisclaimerAccept,
  onEmailSubmit,
  onEmailSkip,
  onRegister,
  onLogin,
}: FunnelManagerProps) {
  // Determine which funnel stage to show
  const getCurrentStage = (): FunnelStage => {
    // Authenticated / registered users skip the entire funnel
    if (sessionState.isRegistered) {
      return 'none';
    }

    // Name must be captured first
    if (!sessionState.name) {
      return 'name';
    }

    // Disclaimer must be accepted before any search
    if (!sessionState.disclaimerAccepted) {
      return 'disclaimer';
    }

    // After 1 search and no email, capture email
    if (sessionState.searchCount === 1 && !sessionState.email) {
      return 'email';
    }

    // After 5 searches and not registered, show search limit gate
    if (sessionState.searchCount >= 5) {
      return 'search-limit';
    }

    return 'none';
  };

  const currentStage = getCurrentStage();

  return (
    <>
      {/* Stage 1: Name Capture */}
      <NameCaptureModal
        isOpen={currentStage === 'name'}
        onSubmit={onNameSubmit}
        brandName={sessionState.brandName}
      />

      {/* Stage 2: Medical Disclaimer */}
      <DisclaimerModal
        isOpen={currentStage === 'disclaimer'}
        onAccept={onDisclaimerAccept}
      />

      {/* Stage 3: Email Capture */}
      <EmailCaptureModal
        isOpen={currentStage === 'email'}
        onSubmit={onEmailSubmit}
        onSkip={onEmailSkip}
      />

      {/* Stage 4: Search Limit Gate */}
      <SearchLimitModal
        isOpen={currentStage === 'search-limit'}
        onRegister={onRegister}
        onLogin={onLogin}
      />
    </>
  );
}
