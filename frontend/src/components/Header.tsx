'use client';

import React from 'react';
import { useTenant } from '@/contexts/TenantContext';
import { useAuth } from '@/contexts/AuthContext';

export function Header() {
  const { tenant } = useTenant();
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <header className="sticky top-0 z-50 bg-brand-white border-b border-brand">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center">
            <h1 className="text-xl font-semibold text-brand">
              {tenant.brandName}
            </h1>
          </div>

          {/* Right section */}
          {isAuthenticated && user && (
            <div className="flex items-center gap-4">
              <span className="text-sm text-brand-secondary">{user.name}</span>
              <button
                onClick={logout}
                className="px-3 py-1 text-sm font-medium text-white bg-brand rounded hover:bg-brand-dark transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
