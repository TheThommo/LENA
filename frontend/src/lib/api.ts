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

export interface ValidatedResult {
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  relevance_score: number;
  keywords: string[];
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
  guardrail_message: string | null;
  sources_queried: string[];
  sources_failed: Record<string, string>;
  total_results: number;
  include_alt_medicine: boolean;
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
    sessionId?: string;
    sessionToken?: string;
    tenantId?: string;
  }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.persona) params.set('persona', options.persona);
  if (options?.sources?.length) params.set('sources', options.sources.join(','));
  if (options?.maxResults) params.set('max_results', String(options.maxResults));
  if (options?.includeAltMedicine !== undefined) {
    params.set('include_alt_medicine', String(options.includeAltMedicine));
  }
  if (options?.tenantId) params.set('tenant_id', options.tenantId);

  const headers: Record<string, string> = {};
  if (options?.sessionToken) {
    headers['Authorization'] = `Bearer ${options.sessionToken}`;
  } else if (options?.sessionId) {
    headers['X-Session-ID'] = options.sessionId;
  }

  const response = await fetch(`${API_BASE}/search?${params}`, { headers });
  if (!response.ok) throw new Error(`Search failed: ${response.statusText}`);
  return response.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health/connections`);
  if (!response.ok) throw new Error(`Health check failed: ${response.statusText}`);
  return response.json();
}
