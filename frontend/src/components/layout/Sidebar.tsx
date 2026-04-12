'use client';

import React from 'react';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onNewSearch: () => void;
  recentSearches: { query: string; time: string }[];
  onSearchClick: (query: string) => void;
  userName?: string;
  isAuthenticated?: boolean;
}

const navItems = [
  { id: 'chat', label: 'Chat', icon: ChatIcon },
  { id: 'research', label: 'My Research', icon: BarChartIcon },
  { id: 'documents', label: 'My Documents', icon: FolderIcon },
  { id: 'brain', label: 'My Brain', icon: BrainIcon },
  { id: 'community', label: 'Community', icon: UsersIcon, badge: 'SOON' },
  { id: 'contribution', label: 'Contribution', icon: UploadIcon, badge: 'SOON' },
  { id: 'how-it-works', label: 'How It Works', icon: BookIcon },
];

export function Sidebar({
  activeView,
  onViewChange,
  onNewSearch,
  recentSearches,
  onSearchClick,
  userName,
  isAuthenticated,
}: SidebarProps) {
  return (
    <aside className="flex flex-col w-[280px] h-full bg-white border-r border-gray-200 shrink-0">
      {/* Logo Section */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg" style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C12 2 14.5 8.5 15.5 9.5C16.5 10.5 22 12 22 12C22 12 16.5 13.5 15.5 14.5C14.5 15.5 12 22 12 22C12 22 9.5 15.5 8.5 14.5C7.5 13.5 2 12 2 12C2 12 7.5 10.5 8.5 9.5C9.5 8.5 12 2 12 2Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 leading-none tracking-tight">
              LENA
            </h1>
            <p className="text-[10px] font-semibold text-lena-500 uppercase tracking-widest">
              Research Agent
            </p>
          </div>
        </div>
      </div>

      {/* New Search Button */}
      <div className="px-4 pb-4">
        <button
          onClick={onNewSearch}
          className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-lena-500 text-white text-sm font-medium rounded-lg hover:bg-lena-700 transition-colors"
        >
          <SearchIcon className="w-4 h-4" />
          New Search
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2">
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const isActive = activeView === item.id;
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  className={`
                    flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium rounded-lg transition-colors
                    ${
                      isActive
                        ? 'text-lena-500 bg-lena-50 border-l-[3px] border-lena-500 pl-[9px]'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 border-l-[3px] border-transparent pl-[9px]'
                    }
                  `}
                >
                  <Icon className="w-[18px] h-[18px] shrink-0" />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full leading-none">
                      {item.badge}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        {/* Recent Searches */}
        {recentSearches.length > 0 && (
          <div className="mt-6 px-2">
            <div className="flex items-center gap-2 mb-3">
              <ClockIcon className="w-3.5 h-3.5 text-gray-400" />
              <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                Recent Searches
              </h3>
            </div>
            <ul className="space-y-1">
              {recentSearches.map((search, idx) => (
                <li key={idx}>
                  <button
                    onClick={() => onSearchClick(search.query)}
                    className="w-full text-left px-2 py-2 rounded-md hover:bg-gray-50 transition-colors group"
                  >
                    <p className="text-sm text-gray-700 truncate group-hover:text-lena-500 transition-colors">
                      {search.query}
                    </p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      {search.time}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 px-4 py-4">
        {isAuthenticated && userName ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-lena-50 text-lena-500 text-xs font-bold">
                {userName.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-gray-700 truncate max-w-[160px]">
                {userName}
              </span>
            </div>
            <button className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors rounded-md hover:bg-gray-50">
              <SettingsIcon className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button className="text-sm text-lena-500 hover:text-lena-700 font-medium transition-colors">
            Sign in for full access
          </button>
        )}
      </div>
    </aside>
  );
}

/* ---------- Inline SVG Icon Components ---------- */

function ChatIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function BarChartIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}

function UsersIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
}

function BookIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function BrainIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" />
      <path d="M10 21v1a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-1" />
      <line x1="9" y1="17" x2="15" y2="17" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
