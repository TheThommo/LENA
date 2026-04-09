'use client';

import React from 'react';
import { useTenant } from '@/contexts/TenantContext';

export function Footer() {
  const { tenant } = useTenant();

  return (
    <footer className="mt-auto bg-brand-white border-t border-brand">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-3 gap-4 text-center">
          {/* Left */}
          <div className="text-left text-sm text-brand-secondary">
            {tenant.footerText}
          </div>

          {/* Center */}
          <div className="text-sm text-brand-secondary">
            <a
              href="#disclaimer"
              className="hover:text-brand transition-colors"
            >
              Medical Disclaimer
            </a>
          </div>

          {/* Right */}
          <div className="text-right text-sm text-brand-muted">
            Cross-referenced. Validated. Evidence-based.
          </div>
        </div>
      </div>
    </footer>
  );
}
