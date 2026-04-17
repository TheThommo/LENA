'use client';

/**
 * Projects — user-owned research folders.
 *
 * Source of truth: the backend `/api/projects` endpoints (Supabase-backed).
 * The currently-selected project id is persisted in localStorage so switching
 * tabs or refreshing the page doesn't reset context.
 *
 * Anonymous users get an empty list + null active id — CRUD is blocked by
 * the backend, and the UI shows a sign-up CTA instead of the create button.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  assignSearchToProject,
  createProject,
  deleteProject,
  listProjects,
  type Project,
  updateProject,
} from '@/lib/api';

const ACTIVE_PROJECT_KEY = 'lena_active_project_id';

interface ProjectsContextType {
  projects: Project[];
  activeProject: Project | null;
  activeProjectId: string | null;
  loading: boolean;
  error: string | null;
  setActiveProjectId: (id: string | null) => void;
  refresh: () => Promise<void>;
  createNew: (body: { name: string; description?: string; color?: string; emoji?: string }) => Promise<Project>;
  rename: (projectId: string, newName: string) => Promise<void>;
  archive: (projectId: string) => Promise<void>;
  unarchive: (projectId: string) => Promise<void>;
  remove: (projectId: string) => Promise<void>;
  assignSearch: (searchId: string, projectId: string | null) => Promise<void>;
}

const ProjectsContext = createContext<ProjectsContextType | undefined>(undefined);

export function ProjectsProvider({ children }: { children: React.ReactNode }) {
  const { token, isAuthenticated } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Rehydrate active project id from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const saved = localStorage.getItem(ACTIVE_PROJECT_KEY);
      if (saved) setActiveProjectIdState(saved);
    } catch {}
  }, []);

  const setActiveProjectId = useCallback((id: string | null) => {
    setActiveProjectIdState(id);
    try {
      if (id) localStorage.setItem(ACTIVE_PROJECT_KEY, id);
      else localStorage.removeItem(ACTIVE_PROJECT_KEY);
    } catch {}
  }, []);

  const refresh = useCallback(async () => {
    if (!isAuthenticated || !token) {
      setProjects([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await listProjects(token);
      setProjects(rows);
      // If the saved active id no longer exists, clear it so the UI doesn't
      // appear to be "inside" a deleted project.
      if (activeProjectId && !rows.find(p => p.id === activeProjectId)) {
        setActiveProjectId(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, token, activeProjectId, setActiveProjectId]);

  useEffect(() => {
    if (isAuthenticated && token) {
      refresh();
    } else {
      setProjects([]);
      setActiveProjectId(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, token]);

  const createNew = useCallback(async (body: { name: string; description?: string; color?: string; emoji?: string }) => {
    if (!token) throw new Error('Sign in to create a project.');
    const p = await createProject(token, body);
    setProjects(prev => [p, ...prev]);
    return p;
  }, [token]);

  const rename = useCallback(async (projectId: string, newName: string) => {
    if (!token) throw new Error('Sign in to rename a project.');
    const updated = await updateProject(token, projectId, { name: newName });
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
  }, [token]);

  const archive = useCallback(async (projectId: string) => {
    if (!token) throw new Error('Sign in to archive a project.');
    const updated = await updateProject(token, projectId, { archived: true });
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
    if (activeProjectId === projectId) setActiveProjectId(null);
  }, [token, activeProjectId, setActiveProjectId]);

  const unarchive = useCallback(async (projectId: string) => {
    if (!token) throw new Error('Sign in to unarchive a project.');
    const updated = await updateProject(token, projectId, { archived: false });
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
  }, [token]);

  const remove = useCallback(async (projectId: string) => {
    if (!token) throw new Error('Sign in to delete a project.');
    await deleteProject(token, projectId);
    setProjects(prev => prev.filter(p => p.id !== projectId));
    if (activeProjectId === projectId) setActiveProjectId(null);
  }, [token, activeProjectId, setActiveProjectId]);

  const assignSearch = useCallback(async (searchId: string, projectId: string | null) => {
    if (!token) throw new Error('Sign in to file a search.');
    await assignSearchToProject(token, searchId, projectId);
    // Cheap: refresh counts
    refresh();
  }, [token, refresh]);

  const activeProject = useMemo(
    () => projects.find(p => p.id === activeProjectId) || null,
    [projects, activeProjectId],
  );

  return (
    <ProjectsContext.Provider
      value={{
        projects,
        activeProject,
        activeProjectId,
        loading,
        error,
        setActiveProjectId,
        refresh,
        createNew,
        rename,
        archive,
        unarchive,
        remove,
        assignSearch,
      }}
    >
      {children}
    </ProjectsContext.Provider>
  );
}

export function useProjects(): ProjectsContextType {
  const ctx = useContext(ProjectsContext);
  if (!ctx) throw new Error('useProjects must be used within a ProjectsProvider');
  return ctx;
}
