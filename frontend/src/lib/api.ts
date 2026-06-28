/**
 * LENA API Client
 * Handles communication with the FastAPI backend.
 */

import { resolveApiBase } from '@/lib/config';

function apiBase(): string {
  return resolveApiBase();
}

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
  study_type?: string;
  cross_validations?: number;
}

export interface SourceAgreement {
  source: string;
  result_count: number;
  overlap_score: number;
  shared_keywords: string[];
  unique_keywords: string[];
  is_consensus: boolean;
  study_types?: string[];
  cross_validations?: number;
}

export interface PulseCrossValidation {
  paper_a: string;
  source_a: string;
  paper_b: string;
  source_b: string;
  similarity: number;
  weight: number;
}

export interface PulseConfidenceBreakdown {
  ratio: number;
  cross_validation_density: number;
  source_coverage: number;
  source_agreement: number;
  coverage_factor: number;
  edge_case_penalty: number;
  contradiction_penalty: number;
}

export interface PulseReport {
  query: string;
  status: 'validated' | 'edge_case' | 'insufficient_validation' | 'pending';
  confidence_ratio: number;
  confidence_breakdown?: PulseConfidenceBreakdown;
  source_count: number;
  sources_attempted?: number;
  sources_failed?: number;
  agreement_count: number;
  consensus_keywords: string[];
  consensus_summary: string;
  validated_count: number;
  edge_case_count: number;
  total_claims_extracted?: number;
  total_cross_validations?: number;
  total_contradictions?: number;
  cross_validations?: PulseCrossValidation[];
  source_agreements: SourceAgreement[];
  validated_results: ValidatedResult[];
  edge_cases: ValidatedResult[];
}

export interface SupplementVerification {
  supplement_name: string;
  brand: string | null;
  trust_score: number;
  trust_level: 'verified' | 'caution' | 'warning' | 'alert';
  trust_breakdown: Record<string, {
    points: number;
    status: string;
    detail: string;
  }>;
  dsld: {
    registered: boolean;
    products_found: number;
    sample_products: { name: string; brand: string; url: string }[];
  };
  fda_recalls: {
    total: number;
    class_i: number;
    class_ii: number;
    class_iii: number;
    recent: {
      recall_number: string;
      product: string;
      reason: string;
      classification: string;
      severity: string;
      firm: string;
      date: string | null;
      status: string;
    }[];
  };
  adverse_events: {
    total: number;
    deaths: number;
    hospitalizations: number;
    serious: number;
  };
  clinical_evidence: {
    papers_found: number;
    cochrane_reviews: number;
  };
  market_presence?: {
    iherb_products_found: number;
    iherb_avg_rating: number;
    iherb_total_reviews: number;
    iherb_brand_url: string;
    iherb_top_products: {
      name: string;
      brand: string;
      rating: number;
      review_count: number;
      price: string | null;
      url: string;
    }[];
  } | null;
  verification_time_ms: number;
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
  supplement_verification?: SupplementVerification | null;
  llm_summary?: string | null;
  attached_content?: AttachedContent[];
}

export interface AttachedContent {
  kind: string;
  source: string;
  title: string;
  text: string;
  chars: number;
  error?: string | null;
}

export interface HealthStatus {
  summary: string;
  all_connected: boolean;
  sources: Record<string, { status: string; results_found?: number }>;
}

// Session API Functions
export async function startSession(): Promise<SessionStartResponse> {
  const response = await fetch(`${apiBase()}/session/start`, { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to start session: ${response.statusText}`);
  return response.json();
}

export async function captureName(sessionId: string, name: string): Promise<any> {
  const response = await fetch(`${apiBase()}/session/${sessionId}/name`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error(`Failed to capture name: ${response.statusText}`);
  return response.json();
}

export async function acceptDisclaimer(sessionId: string): Promise<any> {
  const response = await fetch(`${apiBase()}/session/${sessionId}/disclaimer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accepted: true }),
  });
  if (!response.ok) throw new Error(`Failed to accept disclaimer: ${response.statusText}`);
  return response.json();
}

export async function captureEmail(sessionId: string, email: string): Promise<any> {
  const response = await fetch(`${apiBase()}/session/${sessionId}/email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error(`Failed to capture email: ${response.statusText}`);
  return response.json();
}

export async function getSessionStatus(sessionId: string): Promise<any> {
  const response = await fetch(`${apiBase()}/session/${sessionId}/status`);
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

  const response = await fetch(`${apiBase()}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Registration failed: ${response.statusText}`);
  return response.json();
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${apiBase()}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(`Login failed: ${response.statusText}`);
  return response.json();
}

export async function getCurrentUser(token: string): Promise<UserResponse> {
  const response = await fetch(`${apiBase()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`Failed to get current user: ${response.statusText}`);
  return response.json();
}

export async function logoutUser(token: string): Promise<any> {
  const response = await fetch(`${apiBase()}/auth/logout`, {
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
    profileContext?: string;
    attachedContext?: string;
    attachmentMeta?: { filename: string; kind: string };
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
  if (options?.profileContext) {
    // fetch() rejects header values outside Latin-1 (emojis, smart quotes, etc.).
    // URI-encode so personalised search works for any profile notes.
    headers['X-LENA-Profile-Context'] = encodeURIComponent(
      options.profileContext.slice(0, 2000),
    );
  }
  if (options?.attachedContext) {
    headers['X-LENA-Attached-Context'] = encodeURIComponent(
      options.attachedContext.slice(0, 16000),
    );
  }
  if (options?.attachmentMeta) {
    headers['X-LENA-Attachment-Meta'] = encodeURIComponent(
      JSON.stringify(options.attachmentMeta),
    );
  }
  if (options?.sessionToken) {
    headers['Authorization'] = `Bearer ${options.sessionToken}`;
  } else if (options?.sessionId) {
    headers['X-Session-ID'] = options.sessionId;
  }

  const url = `${apiBase()}/search?${params}`;
  let response: Response;
  try {
    response = await fetch(url, { headers });
  } catch (firstErr) {
    // One retry for transient network blips (common on mobile / Railway cold start).
    try {
      await new Promise((r) => setTimeout(r, 800));
      response = await fetch(url, { headers });
    } catch {
      throw new LenaSystemError();
    }
  }

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body?.detail || '';
    } catch {
      // response body may not be JSON
    }
    if (response.status === 404 || response.status >= 502) {
      throw new LenaSystemError();
    }
    throwForFailedResponse(response.status, detail);
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
  const response = await fetch(`${apiBase()}/billing/status`);
  if (!response.ok) throw new Error(`Billing status failed: ${response.statusText}`);
  return response.json();
}

export async function createCheckoutSession(
  token: string,
  plan: BillingPlan,
): Promise<{ url: string; session_id: string }> {
  const response = await fetch(`${apiBase()}/billing/checkout`, {
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
  const response = await fetch(`${apiBase()}/billing/portal`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Portal failed (${response.status})`);
  }
  return response.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${apiBase()}/health/connections`);
  if (!response.ok) throw new Error(`Health check failed: ${response.statusText}`);
  return response.json();
}

// ── Affiliation / co-branding ───────────────────────────────────────────

export interface AffiliationValidateResponse {
  code: string;
  partner_id: string;
  partner_name: string;
  partner_slug: string;
  segment: string;
  logo_url?: string | null;
  website_url?: string | null;
  benefit_type: string;
  benefit_value: number;
  benefit_description?: string | null;
  co_brand_duration_days?: number | null;
  label?: string | null;
}

export async function validateAffiliationCode(code: string): Promise<AffiliationValidateResponse> {
  const normalized = code.trim().toUpperCase().replace(/\s+/g, '-');
  const response = await fetch(
    `${apiBase()}/affiliation/validate?code=${encodeURIComponent(normalized)}`
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || 'Invalid affiliation code');
  }
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

/** Thrown for plan limits — UI shows UpgradeCTACard, never red errors */
export class LenaUpgradeRequiredError extends Error {
  readonly isUpgradeRequired = true;
  constructor(
    public feature: string,
    message: string,
  ) {
    super(message);
    this.name = 'LenaUpgradeRequiredError';
  }
}

/** Thrown for unexpected server failures — UI shows ContactSupportCard */
export class LenaSystemError extends Error {
  readonly isSystemError = true;
  constructor() {
    super('system');
    this.name = 'LenaSystemError';
  }
}

function throwForFailedResponse(status: number, detail: string): never {
  const msg = typeof detail === 'string' ? detail : '';
  if (status === 402 || status === 403) {
    throw new LenaUpgradeRequiredError('feature', msg || 'Upgrade to Pro to unlock this feature.');
  }
  if (status >= 500) {
    throw new LenaSystemError();
  }
  throw new Error(msg || 'Something went wrong. Please contact us if this keeps happening.');
}

async function readJsonOrThrow(response: Response, action: string) {
  if (!response.ok) {
    let detail = '';
    try { detail = (await response.json())?.detail || ''; } catch {}
    throwForFailedResponse(response.status, detail || `${action} could not be completed`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export type CreateProjectResult =
  | { kind: 'project'; project: Project }
  | { kind: 'upgrade'; message: string; feature: string };

export interface ProjectLimits {
  plan: 'free' | 'pro';
  max_active: number | null;
  active_count: number;
  can_create: boolean;
}

export async function listProjects(token: string): Promise<Project[]> {
  const r = await fetch(`${apiBase()}/projects`, { headers: authHeaders(token) });
  return (await readJsonOrThrow(r, 'List projects')) as Project[];
}

export async function fetchProjectLimits(token: string): Promise<ProjectLimits> {
  const r = await fetch(`${apiBase()}/projects/limits`, { headers: authHeaders(token) });
  return (await readJsonOrThrow(r, 'Fetch project limits')) as ProjectLimits;
}

export async function createProject(
  token: string,
  body: { name: string; description?: string; color?: string; emoji?: string },
): Promise<CreateProjectResult> {
  const r = await fetch(`${apiBase()}/projects`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  let data: Record<string, unknown> = {};
  try {
    data = await r.json();
  } catch {
    /* empty */
  }
  if (data.upgrade_required) {
    return {
      kind: 'upgrade',
      message: String(data.message || ''),
      feature: String(data.feature || 'projects'),
    };
  }
  if (!r.ok) {
    throwForFailedResponse(r.status, String(data.detail || ''));
  }
  return { kind: 'project', project: data as unknown as Project };
}

export async function updateProject(
  token: string,
  projectId: string,
  body: Partial<{ name: string; description: string; color: string; emoji: string; archived: boolean }>,
): Promise<Project | CreateProjectResult> {
  const r = await fetch(`${apiBase()}/projects/${projectId}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  let data: Record<string, unknown> = {};
  try {
    data = await r.json();
  } catch {
    /* empty */
  }
  if (data.upgrade_required) {
    return {
      kind: 'upgrade',
      message: String(data.message || ''),
      feature: String(data.feature || 'projects'),
    };
  }
  if (!r.ok) {
    throwForFailedResponse(r.status, String(data.detail || ''));
  }
  return data as unknown as Project;
}

export async function deleteProject(token: string, projectId: string): Promise<void> {
  const r = await fetch(`${apiBase()}/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  await readJsonOrThrow(r, 'Delete project');
}

export async function listProjectSearches(
  token: string,
  projectId: string,
): Promise<{ project_id: string; searches: ProjectSearch[] }> {
  const r = await fetch(`${apiBase()}/projects/${projectId}/searches`, {
    headers: authHeaders(token),
  });
  return (await readJsonOrThrow(r, 'List project searches')) as { project_id: string; searches: ProjectSearch[] };
}

export async function assignSearchToProject(
  token: string,
  searchId: string,
  projectId: string | null,
): Promise<void> {
  const r = await fetch(`${apiBase()}/projects/searches/${searchId}/assign`, {
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
  const r = await fetch(`${apiBase()}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return readJsonOrThrow(r, 'Request password reset');
}

/**
 * Standalone supplement verification — calls the /supplements/verify endpoint.
 * Use this for on-demand verification (e.g. from a "Verify" button) separate
 * from the auto-verification that happens during search.
 */
export async function verifySupplementStandalone(
  name: string,
  brand?: string,
): Promise<SupplementVerification> {
  const params = new URLSearchParams({ name });
  if (brand) params.set('brand', brand);
  const r = await fetch(`${apiBase()}/supplements/verify?${params}`);
  return readJsonOrThrow(r, 'Verify supplement');
}

// ── User profile, documents, interest, share ─────────────────────────────

export async function fetchProfilePreferences(token: string): Promise<{
  preferences: Record<string, unknown>;
  updated_at: string | null;
}> {
  const r = await fetch(`${apiBase()}/profile/preferences`, { headers: authHeaders(token) });
  return readJsonOrThrow(r, 'Fetch profile') as Promise<{
    preferences: Record<string, unknown>;
    updated_at: string | null;
  }>;
}

export async function saveProfilePreferences(
  token: string,
  preferences: Record<string, unknown>,
): Promise<void> {
  const r = await fetch(`${apiBase()}/profile/preferences`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify({ preferences }),
  });
  await readJsonOrThrow(r, 'Save profile');
}

export async function fetchSavedDocuments(token: string): Promise<{ documents: Record<string, unknown>[] }> {
  const r = await fetch(`${apiBase()}/documents`, { headers: authHeaders(token) });
  return readJsonOrThrow(r, 'Fetch documents') as Promise<{ documents: Record<string, unknown>[] }>;
}

export async function upsertSavedDocumentApi(
  token: string,
  docKey: string,
  payload: Record<string, unknown>,
): Promise<void> {
  const r = await fetch(`${apiBase()}/documents`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ doc_key: docKey, payload }),
  });
  await readJsonOrThrow(r, 'Save document');
}

export async function deleteSavedDocumentApi(token: string, docKey: string): Promise<void> {
  const r = await fetch(`${apiBase()}/documents/${encodeURIComponent(docKey)}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  await readJsonOrThrow(r, 'Delete document');
}

export async function registerFeatureInterest(
  email: string,
  feature: string,
  token?: string | null,
): Promise<{ ok: boolean; message: string }> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${apiBase()}/interest`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ email, feature }),
  });
  return readJsonOrThrow(r, 'Register interest') as Promise<{ ok: boolean; message: string }>;
}

export async function ingestDocument(file: File): Promise<{
  kind: string;
  filename: string;
  title: string;
  text: string;
  chars: number;
}> {
  const form = new FormData();
  form.append('file', file);
  const r = await fetch(`${apiBase()}/ingest`, { method: 'POST', body: form });
  return readJsonOrThrow(r, 'Read document') as Promise<{
    kind: string;
    filename: string;
    title: string;
    text: string;
    chars: number;
  }>;
}

export async function logShareEvent(
  token: string,
  body: {
    search_id?: string;
    recipient_type: string;
    recipient_email?: string;
    note?: string;
    result_title?: string;
  },
): Promise<void> {
  const r = await fetch(`${apiBase()}/share`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  await readJsonOrThrow(r, 'Log share');
}
