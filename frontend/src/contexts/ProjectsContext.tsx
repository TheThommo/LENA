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
  fetchProjectLimits,
  LenaUpgradeRequiredError,
  listProjects,
  type Project,
  type ProjectLimits,
  updateProject,
} from '@/lib/api';

const ACTIVE_PROJECT_KEY_PREFIX = 'lena_active_project_id';

function activeProjectStorageKey(userId: string | null | undefined): string {
  return userId ? `${ACTIVE_PROJECT_KEY_PREFIX}_${userId}` : ACTIVE_PROJECT_KEY_PREFIX;
}

interface ProjectsContextType {
  projects: Project[];
  activeProject: Project | null;
  activeProjectId: string | null;
  loading: boolean;
  error: string | null;
  limits: ProjectLimits | null;
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
  const { token, isAuthenticated, user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limits, setLimits] = useState<ProjectLimits | null>(null);

  // Rehydrate active project id from localStorage (scoped per user)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const key = activeProjectStorageKey(user?.id);
      const saved = localStorage.getItem(key);
      if (saved) setActiveProjectIdState(saved);
      else setActiveProjectIdState(null);
    } catch {}
  }, [user?.id]);

  const setActiveProjectId = useCallback((id: string | null) => {
    setActiveProjectIdState(id);
    try {
      const key = activeProjectStorageKey(user?.id);
      if (id) localStorage.setItem(key, id);
      else localStorage.removeItem(key);
    } catch {}
  }, [user?.id]);

  const refresh = useCallback(async () => {
    if (!isAuthenticated || !token) {
      setProjects([]);
      setLimits(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [rows, quota] = await Promise.all([
        listProjects(token),
        fetchProjectLimits(token),
      ]);
      setProjects(prev => {
        const byId = new Map(rows.map(p => [p.id, p]));
        for (const p of prev) {
          if (!byId.has(p.id)) byId.set(p.id, p);
        }
        return Array.from(byId.values()).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
      });
      setLimits(quota);
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
    const result = await createProject(token, body);
    if (result.kind === 'upgrade') {
      throw new LenaUpgradeRequiredError(result.feature, result.message);
    }
    setProjects(prev => [result.project, ...prev]);
    setLimits(prev => prev ? {
      ...prev,
      active_count: prev.active_count + 1,
      can_create: prev.max_active == null || prev.active_count + 1 < prev.max_active,
    } : prev);
    return result.project;
  }, [token]);

  const rename = useCallback(async (projectId: string, newName: string) => {
    if (!token) throw new Error('Sign in to rename a project.');
    const result = await updateProject(token, projectId, { name: newName });
    if (typeof result === 'object' && result !== null && 'kind' in result && result.kind === 'upgrade') {
      throw new LenaUpgradeRequiredError(result.feature, result.message);
    }
    const updated = result as Project;
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
  }, [token]);

  const archive = useCallback(async (projectId: string) => {
    if (!token) throw new Error('Sign in to archive a project.');
    const result = await updateProject(token, projectId, { archived: true });
    if (typeof result === 'object' && result !== null && 'kind' in result && result.kind === 'upgrade') {
      throw new LenaUpgradeRequiredError(result.feature, result.message);
    }
    const updated = result as Project;
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
    if (activeProjectId === projectId) setActiveProjectId(null);
    setLimits(prev => prev ? {
      ...prev,
      active_count: Math.max(0, prev.active_count - 1),
      can_create: prev.max_active == null || prev.active_count - 1 < prev.max_active,
    } : prev);
  }, [token, activeProjectId, setActiveProjectId]);

  const unarchive = useCallback(async (projectId: string) => {
    if (!token) throw new Error('Sign in to unarchive a project.');
    const result = await updateProject(token, projectId, { archived: false });
    if (typeof result === 'object' && result !== null && 'kind' in result && result.kind === 'upgrade') {
      throw new LenaUpgradeRequiredError(result.feature, result.message);
    }
    const updated = result as Project;
    setProjects(prev => prev.map(p => (p.id === projectId ? updated : p)));
    setLimits(prev => prev ? {
      ...prev,
      active_count: prev.active_count + 1,
      can_create: prev.max_active == null || prev.active_count + 1 < prev.max_active,
    } : prev);
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
        limits,
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
