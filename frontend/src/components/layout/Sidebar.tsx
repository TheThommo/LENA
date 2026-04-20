'use client';

import React, { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';
import { useProjects } from '@/contexts/ProjectsContext';

interface RecentSession {
  id: string;
  firstQuery: string;
  queries: string[];
  time: string;
}

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onNewSearch: () => void;
  recentSessions: RecentSession[];
  /** Called when a recent session is clicked. Passes the session id and a
   *  fallback query (used only if the cached thread can't be restored). */
  onSearchClick: (sessionId: string, fallbackQuery: string) => void;
  userName?: string;
  userEmail?: string;
  isAuthenticated?: boolean;
  onSignIn?: () => void;
  onLogout?: () => void;
}

const navItems = [
  { id: 'chat', label: 'Chat', icon: ChatIcon },
  { id: 'documents', label: 'My Documents', icon: FolderIcon },
  { id: 'sources', label: 'My Sources', icon: BookIcon },
  { id: 'brain', label: 'My Brain', icon: BrainIcon },
  { id: 'community', label: 'Community', icon: UsersIcon, badge: 'SOON' },
  { id: 'contribution', label: 'Contribution', icon: UploadIcon, badge: 'SOON' },
  { id: 'how-it-works', label: 'How It Works', icon: BookIcon },
];

export function Sidebar({
  activeView,
  onViewChange,
  onNewSearch,
  recentSessions,
  onSearchClick,
  userName,
  userEmail,
  isAuthenticated,
  onSignIn,
  onLogout,
}: SidebarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
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
    <aside className="flex flex-col w-[260px] h-full bg-white/80 backdrop-blur-xl border-r border-gray-200/60 shrink-0">
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
          className="flex items-center justify-center gap-2 w-full px-3.5 py-2 bg-lena-500 text-white text-[13px] font-medium rounded-lg hover:bg-lena-700 transition-all shadow-sm hover:shadow"
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
                        ? 'text-lena-600 bg-lena-50'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50/80'
                    }
                  `}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto text-[9px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded-full leading-none tracking-wide">
                      {item.badge}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        {/* Projects */}
        <ProjectsSection
          isAuthenticated={!!isAuthenticated}
          onOpenProject={(id) => { onViewChange('projects'); /* id is set by the section */ void id; }}
          onSignIn={onSignIn}
        />

        {/* Recent Sessions — only for authenticated users. Anonymous visitors
            NEVER see search history, even if stale state briefly exists. */}
        {isAuthenticated && recentSessions.length > 0 && (
          <div className="mt-6 px-2">
            <div className="flex items-center gap-2 mb-3">
              <ClockIcon className="w-3.5 h-3.5 text-gray-400" />
              <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                Recent Sessions
              </h3>
            </div>
            <ul className="space-y-1">
              {recentSessions.map((sess) => (
                <li key={sess.id}>
                  <button
                    onClick={() => onSearchClick(sess.id, sess.firstQuery)}
                    className="w-full text-left px-2 py-2 rounded-md hover:bg-gray-50 transition-colors group"
                  >
                    <p className="text-sm text-gray-700 truncate group-hover:text-lena-500 transition-colors">
                      {sess.firstQuery}
                    </p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      {sess.queries.length > 1
                        ? `${sess.queries.length} queries \u00B7 ${sess.time}`
                        : sess.time}
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
                  {/* Share with Friends */}
                  <button
                    onClick={() => setMenuOpen(false)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <ShareIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <div>
                      <span className="text-sm text-gray-700 group-hover:text-gray-900">Share with Colleagues</span>
                      <span className="ml-2 text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">SOON</span>
                    </div>
                  </button>

                  {/* Get 1 Month Free */}
                  <button
                    onClick={() => setMenuOpen(false)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <GiftIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <div>
                      <span className="text-sm text-gray-700 group-hover:text-gray-900">Get 1 Month Free</span>
                      <span className="ml-2 text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">SOON</span>
                    </div>
                  </button>

                  {/* Upgrade Plan */}
                  <button
                    onClick={() => setMenuOpen(false)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors group"
                  >
                    <SparkleIcon className="w-4 h-4 text-gray-400 group-hover:text-lena-500" />
                    <div>
                      <span className="text-sm text-gray-700 group-hover:text-gray-900">Upgrade Plan</span>
                      <span className="ml-2 text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">SOON</span>
                    </div>
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
}: {
  isAuthenticated: boolean;
  onOpenProject: (projectId: string) => void;
  onSignIn?: () => void;
}) {
  const { projects, activeProjectId, setActiveProjectId, createNew, error } = useProjects();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [inlineErr, setInlineErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const active = projects.filter(p => !p.archived_at);

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
        {active.map(p => {
          const isActive = activeProjectId === p.id;
          return (
            <li key={p.id}>
              <button
                onClick={() => { setActiveProjectId(p.id); onOpenProject(p.id); }}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors group
                  ${isActive ? 'bg-lena-50 text-lena-700' : 'text-gray-700 hover:bg-gray-50'}`}
              >
                <span className="text-[13px] flex-shrink-0">{p.emoji || '📁'}</span>
                <span className="truncate flex-1 text-left">{p.name}</span>
                {p.search_count > 0 && (
                  <span className="text-[10px] text-gray-400 flex-shrink-0">{p.search_count}</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      {isAuthenticated && error && (
        <p className="text-[10px] text-red-500 px-2 mt-2" title={error}>
          {error.length > 60 ? error.slice(0, 60) + '…' : error}
        </p>
      )}
    </div>
  );
}
