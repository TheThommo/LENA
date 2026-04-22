/**
 * LENA API Client
 * Handles communication with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

// Session & Auth Types
export interface SessionStartResponse {
  session_id: string;
  session_token: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface AuthResponse {
  user: UserResponse;
  access_token: string;
}

// Search Domain Types
export interface PersonaInfo {
  detected: string;
  display_name: string;
  tone: string;
  depth: string;
}

export interface SourceAgreement {
  source: string;
  result_count: number;
  overlap_score: number;
  shared_keywords: string[];
  unique_keywords: string[];
  is_consensus: boolean;
}

export type ResultMode = 'all' | 'supplements' | 'herbal' | 'alternatives' | 'outlier';

export interface ValidatedResult {
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  relevance_score: number;
  keywords: string[];
  authors?: string[];
  matched_modes?: ResultMode[];
}

export interface PulseReport {
  query: string;
  status: 'validated' | 'edge_case' | 'insufficient_validation' | 'pending';
  confidence_ratio: number;
  source_count: number;
  agreement_count: number;
  consensus_keywords: string[];
  consensus_summary: string;
  validated_count: number;
  edge_case_count: number;
  source_agreements: SourceAgreement[];
  validated_results: ValidatedResult[];
  edge_cases: ValidatedResult[];
}

export interface SearchResponse {
  search_id: string;
  session_id: string;
  query: string;
  persona: PersonaInfo;
  guardrail_triggered: boolean;
  guardrail_type?: string | null;
  guardrail_message: string | null;
  sources_queried: string[];
  sources_failed: Record<string, string>;
  total_results: number;
  total_pre_scope?: number;
  include_alt_medicine: boolean;
  modes?: ResultMode[];
  response_time_ms: number;
  pulse_report: PulseReport;
  llm_summary?: string | null;
}

export interface HealthStatus {
  summary: string;
  all_connected: boolean;
  sources: Record<string, { status: string; results_found?: number }>;
}

// Session API Functions
export async function startSession(): Promise<SessionStartResponse> {
  const response = await fetch(`${API_BASE}/session/start`, { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to start session: ${response.statusText}`);
  return response.json();
}

export async function captureName(sessionId: string, name: string): Promise<any> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/name`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error(`Failed to capture name: ${response.statusText}`);
  return response.json();
}

export async function acceptDisclaimer(sessionId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/disclaimer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accepted: true }),
  });
  if (!response.ok) throw new Error(`Failed to accept disclaimer: ${response.statusText}`);
  return response.json();
}

export async function captureEmail(sessionId: string, email: string): Promise<any> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error(`Failed to capture email: ${response.statusText}`);
  return response.json();
}

export async function getSessionStatus(sessionId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/session/${sessionId}/status`);
  if (!response.ok) throw new Error(`Failed to get session status: ${response.statusText}`);
  return response.json();
}

// Auth API Functions
export async function registerUser(
  email: string,
  password: string,
  name: string,
  sessionId?: string
): Promise<AuthResponse> {
  const body: any = { email, password, name };
  if (sessionId) body.session_id = sessionId;

  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Registration failed: ${response.statusText}`);
  return response.json();
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(`Login failed: ${response.statusText}`);
  return response.json();
}

export async function getCurrentUser(token: string): Promise<UserResponse> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Failed to get current user: ${response.statusText}`);
  return response.json();
}

export async function logoutUser(token: string): Promise<any> {
  const response = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Logout failed: ${response.statusText}`);
  return response.json();
}

// Search API Functions
export async function searchLiterature(
  query: string,
  options?: {
    persona?: string;
    sources?: string[];
    maxResults?: number;
    includeAltMedicine?: boolean;
    modes?: ResultMode[];
    sessionId?: string;
    sessionToken?: string;
    tenantId?: string;
    projectId?: string;
  }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.persona) params.set('persona', options.persona);
  if (options?.sources?.length) params.set('sources', options.sources.join(','));
  if (options?.maxResults) params.set('max_results', String(options.maxResults));
  if (options?.includeAltMedicine !== undefined) {
    params.set('include_alt_medicine', String(options.includeAltMedicine));
  }
  if (options?.modes?.length) {
    params.set('modes', options.modes.join(','));
  }
  if (options?.tenantId) params.set('tenant_id', options.tenantId);
  if (options?.projectId) params.set('project_id', options.projectId);

  const headers: Record<string, string> = {};
  if (options?.sessionToken) {
    headers['Authorization'] = `Bearer ${options.sessionToken}`;
  } else if (options?.sessionId) {
    headers['X-Session-ID'] = options.sessionId;
  }

  const response = await fetch(`${API_BASE}/search?${params}`, { headers });
  if (!response.ok) {
    // HTTP/2 drops statusText, so read the JSON body (FastAPI returns {detail}).
    let detail = '';
    try {
      const body = await response.json();
      detail = body?.detail || '';
    } catch {
      // response body may not be JSON
    }
    throw new Error(
      `Search failed (${response.status}): ${detail || response.statusText || 'Unknown error'}`,
    );
  }
  return response.json();
}

// ── Billing ─────────────────────────────────────────────────────────
// Thin wrappers around Stripe Checkout. Endpoints return 503 until the
// Stripe keys are set in Railway env. getBillingStatus is safe to call
// without an auth token; createCheckoutSession requires one.

export type BillingPlan = 'pro_monthly' | 'pro_annual' | 'pro_founding';

export interface BillingStatus {
  enabled: boolean;
  publishable_key: string | null;
  plans: { pro_monthly: boolean; pro_annual: boolean; pro_founding: boolean };
  founding_remaining: number;
  founding_max: number;
}

export async function getBillingStatus(): Promise<BillingStatus> {
  const response = await fetch(`${API_BASE}/billing/status`);
  if (!response.ok) throw new Error(`Billing status failed: ${response.statusText}`);
  return response.json();
}

export async function createCheckoutSession(
  token: string,
  plan: BillingPlan,
): Promise<{ url: string; session_id: string }> {
  const response = await fetch(`${API_BASE}/billing/checkout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ plan }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Checkout failed (${response.status})`);
  }
  return response.json();
}

export async function openCustomerPortal(token: string): Promise<{ url: string }> {
  const response = await fetch(`${API_BASE}/billing/portal`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Portal failed (${response.status})`);
  }
  return response.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health/connections`);
  if (!response.ok) throw new Error(`Health check failed: ${response.statusText}`);
  return response.json();
}

// ── Projects ────────────────────────────────────────────────────────────
// Research folders grouping multiple search threads. Auth required.

export interface Project {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  emoji: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  search_count: number;
}

export interface ProjectSearch {
  id: string;
  query: string;
  persona: string | null;
  response_time_ms: number | null;
  total_results: number | null;
  pulse_status: string | null;
  sources_queried: string[] | null;
  sources_succeeded: string[] | null;
  session_id: string | null;
  created_at: string;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

async function readJsonOrThrow(response: Response, action: string) {
  if (!response.ok) {
    let detail = '';
    try { detail = (await response.json())?.detail || ''; } catch {}
    throw new Error(`${action} failed (${response.status}): ${detail || 'Unknown error'}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function listProjects(token: string): Promise<Project[]> {
  const r = await fetch(`${API_BASE}/projects`, { headers: authHeaders(token) });
  return (await readJsonOrThrow(r, 'List projects')) as Project[];
}

export async function createProject(
  token: string,
  body: { name: string; description?: string; color?: string; emoji?: string },
): Promise<Project> {
  const r = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  return (await readJsonOrThrow(r, 'Create project')) as Project;
}

export async function updateProject(
  token: string,
  projectId: string,
  body: Partial<{ name: string; description: string; color: string; emoji: string; archived: boolean }>,
): Promise<Project> {
  const r = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  return (await readJsonOrThrow(r, 'Update project')) as Project;
}

export async function deleteProject(token: string, projectId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  await readJsonOrThrow(r, 'Delete project');
}

export async function listProjectSearches(
  token: string,
  projectId: string,
): Promise<{ project_id: string; searches: ProjectSearch[] }> {
  const r = await fetch(`${API_BASE}/projects/${projectId}/searches`, {
    headers: authHeaders(token),
  });
  return (await readJsonOrThrow(r, 'List project searches')) as { project_id: string; searches: ProjectSearch[] };
}

export async function assignSearchToProject(
  token: string,
  searchId: string,
  projectId: string | null,
): Promise<void> {
  const r = await fetch(`${API_BASE}/projects/searches/${searchId}/assign`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ project_id: projectId }),
  });
  await readJsonOrThrow(r, 'Assign search to project');
}

/**
 * Trigger a password reset email for the given address.
 * Maps to POST /auth/forgot-password on the backend.
 */
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const r = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return readJsonOrThrow(r, 'Request password reset');
}
