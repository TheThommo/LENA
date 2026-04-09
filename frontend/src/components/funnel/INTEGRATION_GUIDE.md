# Freemium Funnel Integration Guide

## Overview
The freemium funnel system controls access to LENA's search functionality through a series of progressive modals. Each modal blocks further interaction until the user completes the step.

## Components

### ModalOverlay
Base reusable modal container with backdrop and animations.
- **Props:**
  - `isOpen: boolean` - Controls visibility
  - `onClose?: () => void` - Optional close handler
  - `children: React.ReactNode` - Modal content
  - `blocking?: boolean` - If true, disables backdrop click and close button

### NameCaptureModal
First funnel step. Captures user name.
- **Props:**
  - `isOpen: boolean`
  - `onSubmit: (name: string) => void` - Fired when user submits name
  - `brandName?: string` - Optional brand name (defaults to "LENA")

### DisclaimerModal
Mandatory medical disclaimer with acceptance checkbox.
- **Props:**
  - `isOpen: boolean`
  - `onAccept: (timestamp: string) => void` - Fired with ISO timestamp when user accepts
- **Note:** This modal is blocking - no close button or backdrop dismiss

### EmailCaptureModal
Captures email after first search result.
- **Props:**
  - `isOpen: boolean`
  - `onSubmit: (email: string) => void` - Fired when valid email submitted
  - `onSkip: () => void` - Fired when user skips
- **Features:** Email validation, optional skip

### SearchLimitModal
Hard gate after 2 free searches.
- **Props:**
  - `isOpen: boolean`
  - `onRegister: () => void` - Fired when user clicks "Create Free Account"
  - `onLogin: () => void` - Fired when user clicks "Sign In"
- **Note:** Blocking modal with no skip option

### FunnelManager
Orchestration component that manages all modals based on session state.

## Usage Example

```typescript
'use client';

import { useState } from 'react';
import { FunnelManager } from '@/components/funnel';

export default function SearchPage() {
  const [sessionState, setSessionState] = useState({
    name: undefined,
    email: undefined,
    disclaimerAccepted: false,
    disclaimerAcceptedAt: undefined,
    searchCount: 0,
    isRegistered: false,
    brandName: 'LENA',
  });

  const handleNameSubmit = (name: string) => {
    setSessionState((prev) => ({ ...prev, name }));
  };

  const handleDisclaimerAccept = (timestamp: string) => {
    setSessionState((prev) => ({
      ...prev,
      disclaimerAccepted: true,
      disclaimerAcceptedAt: timestamp,
    }));
  };

  const handleEmailSubmit = (email: string) => {
    setSessionState((prev) => ({ ...prev, email }));
  };

  const handleEmailSkip = () => {
    // User skipped email capture, continue without it
  };

  const handleRegister = () => {
    // Navigate to registration page
  };

  const handleLogin = () => {
    // Navigate to login page
  };

  const handleSearch = async () => {
    // Only allow if:
    // 1. Name captured
    // 2. Disclaimer accepted
    // 3. Search count < 2 OR user is registered
    if (!sessionState.name || !sessionState.disclaimerAccepted) {
      return; // Funnel will show blocking modal
    }

    if (sessionState.searchCount >= 2 && !sessionState.isRegistered) {
      return; // Funnel will show search limit modal
    }

    // Perform search
    setSessionState((prev) => ({
      ...prev,
      searchCount: prev.searchCount + 1,
    }));
  };

  return (
    <>
      <FunnelManager
        sessionState={sessionState}
        onNameSubmit={handleNameSubmit}
        onDisclaimerAccept={handleDisclaimerAccept}
        onEmailSubmit={handleEmailSubmit}
        onEmailSkip={handleEmailSkip}
        onRegister={handleRegister}
        onLogin={handleLogin}
      />

      {/* Your search UI here */}
      <button onClick={handleSearch}>
        Search
      </button>
    </>
  );
}
```

## Flow Logic

1. **User visits page**
   - If no name: Show NameCaptureModal

2. **User enters name**
   - If no disclaimer accepted: Show DisclaimerModal

3. **User accepts disclaimer**
   - User can now search

4. **First search completes**
   - If no email: Show EmailCaptureModal

5. **User provides email or skips**
   - Can continue searching (second search available)

6. **Second search completes**
   - If not registered: Show SearchLimitModal (blocking)
   - No further searches without registration

## Styling

All modals use:
- Tailwind CSS with `lena-*` color variables (lena-50 through lena-950)
- Inter font family (inherited from Tailwind config)
- Clean, professional medical UI aesthetic
- Consistent card styling: white background, rounded corners, shadow
- Responsive padding and sizing

## Database Logging

The DisclaimerModal provides a timestamp when user accepts. This should be logged:
```typescript
const handleDisclaimerAccept = (timestamp: string) => {
  // Log to database
  await logDisclaimerAcceptance({
    userId: sessionState.name,
    acceptedAt: timestamp,
    ipAddress: undefined, // Set from server if needed
  });
  
  setSessionState((prev) => ({
    ...prev,
    disclaimerAccepted: true,
    disclaimerAcceptedAt: timestamp,
  }));
};
```

## Notes

- All modals are "use client" components
- ModalOverlay prevents body scroll when open
- Blocking modals (DisclaimerModal, SearchLimitModal) cannot be dismissed
- Email validation is basic (regex check) - consider server-side validation on submission
- All text strings are easily customizable through props
- FadeIn animation is defined in Tailwind config (may need to be added if missing)
