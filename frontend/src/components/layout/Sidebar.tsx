'use client';

import React, { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';
import { useProjects } from '@/contexts/ProjectsContext';
import { type Project } from '@/lib/api';
import { type RecentSessionRecord, formatSessionSubtitle, getSessionDisplayTitle } from '@/lib/sessionTime';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onNewSearch: () => void;
  recentSessions: RecentSessionRecord[];
  /** Called when a recent session is clicked. Passes the session id and a
   *  fallback query (used only if the cached thread can't be restored). */
  onSearchClick: (sessionId: string, fallbackQuery: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  onRenameSession?: (sessionId: string, title: string) => void;
  userName?: string;
  userEmail?: string;
  isAuthenticated?: boolean;
  onSignIn?: () => void;
  onLogout?: () => void;
  onUpgrade?: () => void;
  onShareReferral?: () => void;
}

const navItems = [
  { id: 'chat', label: 'Chat', icon: ChatIcon },
  { id: 'documents', label: 'My Documents', icon: FolderIcon },
  { id: 'how-it-works', label: 'How It Works', icon: BookIcon },
  { id: 'community', label: 'Community', icon: UsersIcon },
  { id: 'contribution', label: 'Contribution', icon: UploadIcon },
];

export function Sidebar({
  activeView,
  onViewChange,
  onNewSearch,
  recentSessions,
  onSearchClick,
  onDeleteSession,
  onRenameSession,
  userName,
  userEmail,
  isAuthenticated,
  onSignIn,
  onLogout,
  onUpgrade,
  onShareReferral,
}: SidebarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [referralCopied, setReferralCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  return (
    <aside className="flex flex-col w-[260px] h-full bg-white/95 backdrop-blur-xl border-r border-slate-200/80 shrink-0 shadow-[1px_0_0_rgba(15,23,42,0.04)]">
      {/* Logo Section */}
      <div className="px-5 pt-5 pb-3">
        <Image
          src={branding.logoSrc}
          alt={branding.name}
          width={220}
          height={72}
          className="object-contain"
          priority
        />
      </div>

      {/* New Search Button */}
      <div className="px-3 pb-3">
        <button
          onClick={onNewSearch}
          className="flex items-center justify-center gap-2 w-full px-3.5 py-2 bg-lena-500 text-white text-[13px] font-medium rounded-lg hover:bg-lena-700 transition-all shadow-sm hover:shadow-md"
        >
          <SearchIcon className="w-3.5 h-3.5" />
          New Search
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2">
        <ul className="space-y-px">
          {navItems.map((item) => {
            const isActive = activeView === item.id;
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  className={`
                    flex items-center gap-2.5 w-full px-3 py-2 text-[13px] font-medium rounded-md transition-all
                    ${
                      isActive
                        ? 'text-lena-700 bg-lena-50/90 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/90'
                    }
                  `}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>

        {/* Projects */}
        <ProjectsSection
          isAuthenticated={!!isAuthenticated}
          onOpenProject={() => { onViewChange('projects'); }}
          onSignIn={onSignIn}
          recentSessions={recentSessions}
          onSearchClick={onSearchClick}
          onDeleteSession={onDeleteSession}
          onRenameSession={onRenameSession}
        />

        {/* Recent Sessions — only UNFILED sessions show here; project-filed
            sessions are nested under their project above. */}
        {isAuthenticated && recentSessions.filter(s => !s.projectId).length > 0 && (
          <div className="mt-6 px-2">
            <div className="flex items-center gap-2 mb-3">
              <ClockIcon className="w-3.5 h-3.5 text-gray-400" />
              <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                Recent Sessions
              </h3>
            </div>
            <ul className="space-y-1">
              {recentSessions.filter(s => !s.projectId).map((sess) => (
                <SessionRow
                  key={sess.id}
                  session={sess}
                  variant="recent"
                  onOpen={() => onSearchClick(sess.id, sess.firstQuery)}
                  onDelete={onDeleteSession}
                  onRename={onRenameSession}
                />
              ))}
            </ul>
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 px-4 py-4">
        {isAuthenticated && userName ? (
          <div className="relative" ref={menuRef}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center justify-center w-7 h-7 rounded-full bg-lena-50 text-lena-500 text-xs font-bold">
                  {userName.charAt(0).toUpperCase()}
                </div>
                <span className="text-sm font-medium text-gray-700 truncate max-w-[160px]">
                  {userName}
                </span>
              </div>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors rounded-md hover:bg-gray-50"
              >
                <SettingsIcon className="w-4 h-4" />
              </button>
            </div>

            {/* Profile Dropdown Menu */}
            {menuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden z-50">
                {/* User info header */}
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-900 truncate">{userName}</p>
                  {userEmail && (
                    <p className="text-[11px] text-gray-400 truncate mt-0.5">{userEmail}</p>
                  )}
                  <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded-full border border-emerald-200">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    Free Plan
                  </div>
                </div>

                <div className="py-1.5">
                  {/* Profile Settings */}
                  <button
                    onClick={() => { setMenuOpen(false); onViewChange('profile'); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <SettingsIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Profile &amp; Settings</span>
                  </button>

                  <div className="border-t border-gray-100 my-1.5" />

                  {/* Share with Colleagues */}
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onShareReferral?.();
                      setReferralCopied(true);
                      setTimeout(() => setReferralCopied(false), 2500);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <ShareIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">
                      {referralCopied ? 'Referral link copied!' : 'Share with Colleagues'}
                    </span>
                  </button>

                  {/* Get 1 Month Free */}
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onShareReferral?.();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <GiftIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Get 1 Month Free</span>
                  </button>

                  {/* Upgrade Plan */}
                  <button
                    onClick={() => { setMenuOpen(false); onUpgrade?.(); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <SparkleIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Upgrade Plan</span>
                  </button>

                  <div className="border-t border-gray-100 my-1.5" />

                  {/* Contact Us */}
                  <a
                    href="mailto:hello@lena-research.com"
                    onClick={() => setMenuOpen(false)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <MailIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Contact Us</span>
                  </a>

                  <div className="border-t border-gray-100 my-1.5" />

                  {/* Sign Out */}
                  <button
                    onClick={() => { setMenuOpen(false); onLogout?.(); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-red-50 transition-colors group"
                  >
                    <LogOutIcon className="w-4 h-4 text-gray-400 group-hover:text-red-500" />
                    <span className="text-sm text-gray-700 group-hover:text-red-600">Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={onSignIn}
            className="text-sm text-lena-500 hover:text-lena-700 font-medium transition-colors"
          >
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

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function ShareIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

function GiftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 12 20 22 4 22 4 12" /><rect x="2" y="7" width="20" height="5" />
      <line x1="12" y1="22" x2="12" y2="7" /><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" />
      <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
    </svg>
  );
}

function SparkleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function MailIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

function LogOutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function PencilIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
    </svg>
  );
}

/**
 * One research thread in the sidebar — supports open, rename, delete.
 */
function SessionRow({
  session,
  variant,
  onOpen,
  onDelete,
  onRename,
}: {
  session: RecentSessionRecord;
  variant: 'recent' | 'project';
  onOpen: () => void;
  onDelete?: (sessionId: string) => void;
  onRename?: (sessionId: string, title: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const label = getSessionDisplayTitle(session);
  const isRecent = variant === 'recent';

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const startEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDraft(label);
    setEditing(true);
  };

  const commitEdit = () => {
    onRename?.(session.id, draft);
    setEditing(false);
  };

  const cancelEdit = () => {
    setEditing(false);
    setDraft('');
  };

  if (editing) {
    return (
      <li>
        <div className={`px-2 ${isRecent ? 'py-1.5' : 'py-1'}`}>
          <input
            ref={inputRef}
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') commitEdit();
              if (e.key === 'Escape') cancelEdit();
            }}
            onBlur={commitEdit}
            placeholder="Session name"
            className={`w-full border border-lena-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-lena-200 bg-white ${
              isRecent ? 'text-sm' : 'text-[12px]'
            }`}
          />
          <p className="text-[10px] text-gray-400 mt-1">Enter to save · Esc to cancel</p>
        </div>
      </li>
    );
  }

  return (
    <li>
      <div className={`flex items-stretch gap-0.5 ${isRecent ? 'group' : 'group/sess'}`}>
        <button
          type="button"
          onClick={onOpen}
          className={`flex-1 min-w-0 text-left rounded-md transition-colors ${
            isRecent
              ? 'px-2 py-2 hover:bg-gray-50'
              : 'px-1.5 py-1 text-[12px] text-gray-600 hover:text-lena-600 hover:bg-lena-50/60'
          }`}
          title={session.firstQuery}
        >
          {isRecent ? (
            <>
              <p className="text-sm text-gray-700 truncate group-hover:text-lena-500 transition-colors">
                {label}
              </p>
              <p className="text-[11px] text-gray-400 mt-0.5">
                {formatSessionSubtitle(session)}
              </p>
            </>
          ) : (
            <span className="truncate block">
              {label}
              {session.queries.length > 1 && (
                <span className="ml-1 text-[10px] text-gray-400">({session.queries.length})</span>
              )}
            </span>
          )}
        </button>
        {onRename && (
          <button
            type="button"
            onClick={startEdit}
            className={`flex-shrink-0 self-center p-1 rounded-md text-gray-300 opacity-0 ${
              isRecent ? 'group-hover:opacity-100 mr-0.5' : 'group-hover/sess:opacity-100'
            } hover:text-lena-600 hover:bg-lena-50 transition-all`}
            title="Rename session"
            aria-label="Rename session"
          >
            <PencilIcon className={isRecent ? 'w-3.5 h-3.5' : 'w-3 h-3'} />
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(session.id);
            }}
            className={`flex-shrink-0 self-center p-1 rounded-md text-gray-300 opacity-0 ${
              isRecent ? 'group-hover:opacity-100 mr-1 hover:bg-red-50' : 'group-hover/sess:opacity-100'
            } hover:text-red-500 transition-all`}
            title="Delete session"
            aria-label="Delete session"
          >
            <TrashIcon className={isRecent ? 'w-3.5 h-3.5' : 'w-3 h-3'} />
          </button>
        )}
      </div>
    </li>
  );
}

/**
 * One project row with rename, archive, delete, and nested sessions.
 */
function ProjectRow({
  project,
  isActive,
  filed,
  isArchived,
  onOpenProject,
  onSearchClick,
  onDeleteSession,
  onRenameSession,
}: {
  project: Project;
  isActive: boolean;
  filed: RecentSessionRecord[];
  isArchived?: boolean;
  onOpenProject: (projectId: string) => void;
  onSearchClick?: (sessionId: string, fallbackQuery: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  onRenameSession?: (sessionId: string, title: string) => void;
}) {
  const { setActiveProjectId, rename, archive, unarchive, remove } = useProjects();
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(project.name);
  const [busy, setBusy] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const commitRename = async () => {
    const name = draft.trim();
    if (!name || name === project.name) {
      setEditing(false);
      setDraft(project.name);
      return;
    }
    setBusy(true);
    try {
      await rename(project.id, name);
      setEditing(false);
    } catch {
      setDraft(project.name);
    } finally {
      setBusy(false);
    }
  };

  if (editing) {
    return (
      <li className="px-1 py-1">
        <input
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') commitRename();
            if (e.key === 'Escape') { setEditing(false); setDraft(project.name); }
          }}
          onBlur={commitRename}
          disabled={busy}
          className="w-full text-sm border border-lena-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-lena-200 bg-white"
        />
      </li>
    );
  }

  return (
    <li>
      <div className="flex items-center gap-0.5 group/proj">
        <button
          type="button"
          onClick={() => { setActiveProjectId(project.id); onOpenProject(project.id); }}
          className={`flex-1 min-w-0 flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors
            ${isActive ? 'bg-lena-50 text-lena-700' : 'text-gray-700 hover:bg-gray-50'}`}
        >
          <span className="text-[13px] flex-shrink-0">{project.emoji || '📁'}</span>
          <span className="truncate flex-1 text-left">{project.name}</span>
          {(project.search_count > 0 || filed.length > 0) && (
            <span className="text-[10px] text-gray-400 flex-shrink-0">
              {Math.max(project.search_count, filed.length)}
            </span>
          )}
        </button>
        <div className="relative flex-shrink-0" ref={menuRef}>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setMenuOpen(v => !v); }}
            className="p-1 rounded text-gray-300 opacity-0 group-hover/proj:opacity-100 hover:text-gray-600 hover:bg-gray-100 transition-all"
            aria-label="Project options"
          >
            <MoreIcon className="w-3.5 h-3.5" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 z-50 w-36 bg-white border border-gray-200 rounded-lg shadow-lg py-1 text-xs">
              <button
                type="button"
                className="w-full text-left px-3 py-1.5 hover:bg-gray-50"
                onClick={() => { setMenuOpen(false); setEditing(true); setDraft(project.name); }}
              >
                Rename
              </button>
              {isArchived ? (
                <button
                  type="button"
                  className="w-full text-left px-3 py-1.5 hover:bg-gray-50"
                  onClick={async () => { setMenuOpen(false); await unarchive(project.id); }}
                >
                  Unarchive
                </button>
              ) : (
                <button
                  type="button"
                  className="w-full text-left px-3 py-1.5 hover:bg-gray-50"
                  onClick={async () => { setMenuOpen(false); await archive(project.id); }}
                >
                  Archive
                </button>
              )}
              <button
                type="button"
                className="w-full text-left px-3 py-1.5 hover:bg-red-50 text-red-600"
                onClick={async () => {
                  setMenuOpen(false);
                  if (window.confirm(`Delete "${project.name}"? Searches will be unfiled.`)) {
                    await remove(project.id);
                  }
                }}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
      {!isArchived && filed.length > 0 && onSearchClick && (
        <ul className="ml-6 mt-0.5 mb-1 space-y-0.5 border-l border-gray-100 pl-2">
          {filed.slice(0, 12).map(sess => (
            <SessionRow
              key={sess.id}
              session={sess}
              variant="project"
              onOpen={() => onSearchClick(sess.id, sess.firstQuery)}
              onDelete={onDeleteSession}
              onRename={onRenameSession}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function MoreIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
    </svg>
  );
}

/**
 * ProjectsSection — lists the user's active projects and supports inline
 * create. Clicking a project makes it active (affects subsequent searches)
 * and navigates to the Projects view.
 *
 * Anonymous users see a soft CTA that opens the signup flow — projects
 * require registration because they have to persist across devices.
 */
function ProjectsSection({
  isAuthenticated,
  onOpenProject,
  onSignIn,
  recentSessions,
  onSearchClick,
  onDeleteSession,
  onRenameSession,
}: {
  isAuthenticated: boolean;
  onOpenProject: (projectId: string) => void;
  onSignIn?: () => void;
  recentSessions?: RecentSessionRecord[];
  onSearchClick?: (sessionId: string, fallbackQuery: string) => void;
  onDeleteSession?: (sessionId: string) => void;
  onRenameSession?: (sessionId: string, title: string) => void;
}) {
  const { projects, activeProjectId, setActiveProjectId, createNew, error } = useProjects();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [inlineErr, setInlineErr] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const active = projects.filter(p => !p.archived_at);
  const archived = projects.filter(p => p.archived_at);

  useEffect(() => {
    if (creating) inputRef.current?.focus();
  }, [creating]);

  const submit = async () => {
    const name = newName.trim();
    if (!name) return;
    setSubmitting(true);
    setInlineErr(null);
    try {
      const p = await createNew({ name });
      setActiveProjectId(p.id);
      onOpenProject(p.id);
      setNewName('');
      setCreating(false);
    } catch (e) {
      setInlineErr(e instanceof Error ? e.message : 'Could not create project');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-6 px-2">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FolderIcon className="w-3.5 h-3.5 text-gray-400" />
          <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
            Projects
          </h3>
        </div>
        {isAuthenticated && !creating && (
          <button
            onClick={() => setCreating(true)}
            className="p-1 text-gray-400 hover:text-lena-500 rounded transition-colors"
            title="New project"
          >
            <PlusIcon className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {!isAuthenticated && (
        <button
          onClick={onSignIn}
          className="w-full text-left px-2 py-2 text-xs text-gray-500 hover:text-lena-500 rounded hover:bg-gray-50 transition-colors"
        >
          Sign up to save research to projects
        </button>
      )}

      {isAuthenticated && creating && (
        <div className="mb-2">
          <input
            ref={inputRef}
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') submit();
              if (e.key === 'Escape') { setCreating(false); setNewName(''); setInlineErr(null); }
            }}
            placeholder="e.g. SGLT2 in HFpEF"
            disabled={submitting}
            className="w-full text-sm border border-lena-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-lena-200 bg-white"
          />
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px] text-gray-400">Enter to save · Esc to cancel</span>
            {inlineErr && (
              <span className="text-[10px] text-red-500 truncate ml-2" title={inlineErr}>{inlineErr}</span>
            )}
          </div>
        </div>
      )}

      {isAuthenticated && active.length === 0 && !creating && (
        <p className="text-xs text-gray-400 px-2">
          No projects yet. Click + to group your research.
        </p>
      )}

      <ul className="space-y-0.5">
        {active.map(p => (
          <ProjectRow
            key={p.id}
            project={p}
            isActive={activeProjectId === p.id}
            filed={(recentSessions || []).filter(s => s.projectId === p.id)}
            onOpenProject={onOpenProject}
            onSearchClick={onSearchClick}
            onDeleteSession={onDeleteSession}
            onRenameSession={onRenameSession}
          />
        ))}
      </ul>

      {isAuthenticated && archived.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowArchived(v => !v)}
            className="text-[10px] text-gray-400 hover:text-gray-600 px-2 uppercase tracking-wide"
          >
            {showArchived ? 'Hide' : 'Show'} archived ({archived.length})
          </button>
          {showArchived && (
            <ul className="space-y-0.5 mt-1">
              {archived.map(p => (
                <ProjectRow
                  key={p.id}
                  project={p}
                  isActive={activeProjectId === p.id}
                  filed={[]}
                  isArchived
                  onOpenProject={onOpenProject}
                />
              ))}
            </ul>
          )}
        </div>
      )}

      {isAuthenticated && error && (
        <p className="text-[10px] text-red-500 px-2 mt-2" title={error}>
          {error.length > 60 ? error.slice(0, 60) + '…' : error}
        </p>
      )}
    </div>
  );
}
