# Buddees Admin Console - Technical Architecture Brief

**Purpose:** Complete technical reference for replicating the buddees.ai/admin.html admin console architecture in another project (e.g., Cursor).

**Last updated:** June 17, 2026

---

## 1. High-Level Architecture

The admin console is a **single-file SPA** (Single Page Application) built as one self-contained `admin.html` file (approximately 4,800 lines). It has zero frontend dependencies beyond two CDN-loaded libraries and communicates with a thin PHP API layer that proxies to Airtable as the primary data store.

```
admin.html (SPA, ~4800 lines)
    |
    |-- CSS (inline <style>, ~824 lines)
    |-- HTML structure (sections toggled by JS, ~1270 lines)
    |-- JavaScript (inline <script>, ~2700 lines)
    |
    v
PHP API Layer (GoDaddy shared hosting)
    |
    |-- _auth.php ............ Session-based authentication
    |-- airtable.php ......... Admin-only Airtable proxy (READ/WRITE)
    |-- public-lead.php ...... Public write-only proxy (anonymous)
    |-- send-lead-email.php .. Email nurture system (Resend API)
    |-- openai.php ........... OpenAI proxy (rate-limited)
    |-- stripe.php ........... Stripe checkout session creator
    |-- stripe-webhook.php ... Stripe webhook handler (signature verified)
    |-- config.php ........... Secrets (gitignored, server-only)
    |
    v
External Services
    |-- Airtable (database, all tables)
    |-- Resend (transactional email)
    |-- Stripe (payments + webhooks)
    |-- OpenAI (chat AI for website agents)
```

### Why Single-File?

No build step, no bundler, no framework. Deploys via FTP or git push to GoDaddy shared hosting. The entire frontend is one HTML file. This was a deliberate choice for speed of iteration on a marketing site admin panel that doesn't need React/Vue complexity.

---

## 2. Frontend Architecture

### 2.1 Stack

| Layer | Technology |
|-------|-----------|
| Fonts | Google Fonts: DM Sans (UI) + DM Mono (data/numbers) |
| Charts | Chart.js via CDN (`https://cdn.jsdelivr.net/npm/chart.js`) |
| CSS | Inline `<style>` block, CSS custom properties (design tokens) |
| JS | Vanilla JavaScript, no framework, no build step |

### 2.2 Design System (CSS Variables)

The console uses a dark theme with a carefully defined token system. Here are the core variables:

```css
:root {
  /* Backgrounds (3-tier depth) */
  --bg-base: #07091A;       /* Page background */
  --bg-surface: #0D1025;    /* Cards, sidebar */
  --bg-elevated: #141830;   /* Inputs, hover states, nested cards */

  /* Borders */
  --border: rgba(255, 255, 255, 0.07);        /* Subtle dividers */
  --border-strong: rgba(255, 255, 255, 0.12);  /* Active/hover borders */

  /* Text */
  --text-primary: #FFFFFF;
  --text-secondary: rgba(255, 255, 255, 0.55);
  --text-muted: rgba(255, 255, 255, 0.28);

  /* Accent palette */
  --accent-red: #FF3B30;
  --accent-blue: #0066FF;
  --accent-green: #34D399;
  --accent-amber: #FFB400;
  --gradient: linear-gradient(135deg, #FF3B30, #0066FF);

  /* Agent-specific colors */
  --tabby: #00BFA5;   /* Teal */
  --jack: #FF3B30;    /* Red */
  --marco: #0066FF;   /* Blue */
  --cassie: #7C3AED;  /* Purple */
}
```

### 2.3 Layout Structure

The layout is a fixed sidebar + topbar + scrollable main content area:

```
+----------------------------------------------------------+
|  SIDEBAR (220px fixed)  |  TOPBAR (56px fixed)           |
|                         |----------------------------------|
|  Logo                   |                                  |
|  Menu Items             |  MAIN WRAPPER                    |
|    - Overview           |    (scrollable content)          |
|    - Agent Analytics    |                                  |
|    - Leads              |    <section> elements            |
|    - Voice vs Chat      |    toggled via .active class     |
|    - ROI Calculator     |                                  |
|    - Business Health    |                                  |
|    - Affiliates         |                                  |
|    - Super Admin        |                                  |
|                         |                                  |
|  Sync Status            |                                  |
|  Refresh Button         |                                  |
|  Logout Button          |                                  |
+----------------------------------------------------------+
```

CSS implementation:

```css
.sidebar {
  width: 220px;
  position: fixed;
  height: 100%;
  left: 0;
  top: 0;
  z-index: 50;
  overflow-y: auto;
}

.topbar {
  position: fixed;
  top: 0;
  left: 220px;
  right: 0;
  height: 56px;
  z-index: 40;
}

.main-wrapper {
  margin-left: 220px;
  margin-top: 56px;
  width: calc(100% - 220px);
  height: calc(100% - 56px);
  overflow-y: auto;
  overflow-x: hidden;
}
```

### 2.4 Section/Tab Navigation Pattern

Each page is a `<section>` element with an `id`. Only one has `class="active"` at a time. Tab switching is done via:

```javascript
function switchTab(sectionId, el) {
  // Hide all sections
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  // Deactivate all sidebar items
  document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
  // Show selected section
  document.getElementById(sectionId).classList.add('active');
  // Activate sidebar item
  if (el) el.classList.add('active');
  // Update topbar title
  document.getElementById('topbarTitle').textContent = titles[sectionId] || 'Dashboard';
}
```

HTML structure:

```html
<section id="overview" class="section active">...</section>
<section id="agents" class="section">...</section>
<section id="leads" class="section">...</section>
<!-- etc. -->
```

### 2.5 Sections (8 total)

| Section ID | Name | Purpose |
|-----------|------|---------|
| `overview` | Overview | KPI stat cards, conversion funnel, geography, traffic sources, peak hours, growth velocity |
| `agents` | Agent Analytics | Per-agent conversation counts, CTA rates, voice metrics, 30-day trends, session drill-down table |
| `leads` | Leads | Lead scoring, sortable table, search/filter, drill-down modal, email nurture, follow-up alerts, graduate applications |
| `intelligence` | Voice vs Chat | Side-by-side channel comparison, cost efficiency, lead source breakdown, daily activity timeline, ROI scores |
| `roi` | ROI Calculator | ROI lead analytics from calculator submissions, average inputs, state breakdown, leads table |
| `health` | Business Health | Platform cost intelligence (chat + voice), budget tracking, daily spend chart, system status, voice call logs with transcripts |
| `affiliates` | Affiliates | Coming soon section, application management, commission structure display |
| `superadmin` | Super Admin | API spec reference, user management, promo codes, credits, audit log. PIN-protected actions. |

---

## 3. Authentication System

### 3.1 Flow

```
1. Page loads -> JS calls GET /api/_auth.php?action=check
2. If authenticated=true -> show dashboard, skip login
3. If not -> show login screen
4. User enters password -> POST /api/_auth.php?action=login { password }
5. Server validates against BUDDEES_ADMIN_PASSWORD constant
6. Server sets HttpOnly session cookie (BUDDEES_ADMIN)
7. All subsequent API calls include credentials: 'include'
8. Any 401 response triggers automatic logout
```

### 3.2 Server-Side Auth (_auth.php)

Key design decisions:

**Session configuration (secure defaults):**
```php
ini_set('session.cookie_httponly', 1);     // No JS access to cookie
ini_set('session.cookie_secure',  1);      // HTTPS only
ini_set('session.cookie_samesite', 'Strict'); // No cross-site
ini_set('session.use_strict_mode', 1);     // Reject uninitialized session IDs
ini_set('session.name', 'BUDDEES_ADMIN');  // Custom session name
```

**Dual-use file pattern:** `_auth.php` works both as a standalone endpoint AND as an includable module:

```php
// When included by other files:
require_once __DIR__ . '/_auth.php';
requireAdmin();  // Guards the endpoint

// When called directly as an endpoint:
if (basename($_SERVER['SCRIPT_FILENAME']) === '_auth.php') {
  // Handle login, logout, check, elevate actions
}
```

**Guard functions:**
```php
function isAdmin(): bool { ... }
function isSuperAdmin(): bool { ... }
function requireAdmin(): void { /* 401 if not admin */ }
function requireSuperAdmin(): void { /* 403 if not super admin */ }
```

**Two-tier authentication:**
- **Admin:** Password login, can view all data and manage leads
- **Super Admin:** Requires additional password (elevation), can manage users, promo codes, reset budget

### 3.3 Rate Limiting

File-based rate limiter (no dependencies like APCu/Redis needed):

```php
function rateLimitCheck(string $key, int $maxAttempts, int $windowSeconds): void {
  $dir = __DIR__ . '/_rate_limit_cache';
  $file = $dir . '/' . md5($key) . '.json';
  // Stores timestamps as JSON array, prunes old entries, returns 429 if exceeded
}
```

Rate limits by endpoint:
- Login: 5 attempts / 5 minutes per IP
- Public lead capture: 30 requests / 60 seconds per IP
- OpenAI proxy: 20 requests / 60 seconds per IP (admin sessions bypass)
- Registration email: 5 / 10 minutes per IP
- Support request: 5 / 10 minutes per IP

### 3.4 Client-Side Auth Code

```javascript
// Login
async function attemptLogin() {
  const resp = await fetch('/api/_auth.php?action=login', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  const data = await resp.json();
  if (data.success) { /* show dashboard */ }
}

// Session check on page load
window.addEventListener('load', async () => {
  const resp = await fetch('/api/_auth.php?action=check', { credentials: 'include' });
  const data = await resp.json();
  if (data.authenticated) { /* show dashboard */ }
});

// Every API call includes credentials
const response = await fetch(url, { credentials: 'include' });
if (response.status === 401) { logout(); return []; }
```

### 3.5 Super Admin PIN Overlay

Protected actions (add user, revoke access, create promo, issue credits, reset budget) require super admin verification:

```javascript
function requirePin(callback) {
  pendingPinAction = callback;
  document.getElementById('pinOverlay').classList.add('active');
  document.getElementById('superAdminInput').focus();
}

async function checkPin() {
  const pin = document.getElementById('superAdminInput').value;
  const resp = await fetch('/api/_auth.php?action=elevate', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  });
  if (data.success) { pendingPinAction(); dismissPin(); }
}
```

---

## 4. Data Layer

### 4.1 Airtable as Database

All data lives in Airtable. The admin console reads from 6 tables:

| Table Name | Purpose | Key Fields |
|-----------|---------|------------|
| `Early Access` | Lead records | Name, Email, Trade, Country, Phone, Business Name, Source, Agent, Location, Lead Status, Submitted |
| `Conversations` | Chat sessions | Name, Email, Agent, Question, First Message, Last Message, Transcript, CTA Shown, CTA Converted, Voice Call Started, Date, Cost, Token Count |
| `Voice Calls` | Voice call logs | Name, Email, Agent, Duration Seconds, Transcript, Status, Est Cost, Date |
| `Page Views` | Website analytics | Page, Referrer, User Agent, Timestamp, Country, State, City, Source |
| `Graduate Applications` | Job applications | Name, Email, College, Student ID, Date, Status |
| `ROI Analytics` | ROI calculator runs | Staff, Wage, CallsPerDay, MissedPerDay, JobValue, TotalSavings, BreakEven, Plan, State |

### 4.2 API Proxy Pattern

The PHP layer is a thin proxy. It never processes or transforms data. It just:

1. Validates authentication
2. Forwards the request to Airtable's API
3. Returns the raw response

**Admin proxy (airtable.php):**
```php
requireAdmin();
$url = "https://api.airtable.com/v0/" . AIRTABLE_BASE_ID . "/{$table}{$recordId}{$queryString}";
// Forward method (GET/POST/PATCH), headers, body -> return raw response
```

**Public proxy (public-lead.php):**
- Strict table allowlist (7 tables)
- Per-table field allowlist (each table has explicit writable fields)
- Strips unknown fields
- Truncates strings to 5000 chars
- Rate limited
- POST and PATCH only

### 4.3 Pagination Pattern

Airtable returns max 100 records per request. The console handles pagination automatically:

```javascript
async function fetchAirtable(table) {
  const allRecords = [];
  let offset = null;
  do {
    let url = `/api/airtable.php?table=${encodeURIComponent(table)}`;
    if (offset) url += `&offset=${encodeURIComponent(offset)}`;
    const response = await fetch(url, { credentials: 'include' });
    if (response.status === 401) { logout(); return []; }
    const data = await response.json();
    if (data.records) allRecords.push(...data.records);
    offset = data.offset || null;  // Airtable provides next page offset
  } while (offset);
  return allRecords;
}
```

### 4.4 Data Loading Strategy

On login, all sections load in parallel:

```javascript
async function loadAllData() {
  await Promise.all([
    loadOverview(),
    loadAgentAnalytics(),
    loadLeads(),
    loadAffiliates(),
    loadROI(),
    loadHealth(),
    loadIntelligence()
  ]);
}
```

Each load function fetches only the tables it needs. Some tables are fetched by multiple sections (e.g., `Early Access` is used by Overview, Leads, and ROI). This means some duplicate fetches happen, but it keeps each section self-contained and independently refreshable.

### 4.5 Caching Pattern

Client-side caches for frequently-accessed data:

```javascript
let leadsDataCache = [];     // Scored lead objects for the Leads section
let gradsDataCache = [];     // Graduate applications
let roiLeadsCache = [];      // ROI calculator leads
let questionsDataCache = []; // Conversations for question analysis
window._cachedConversations; // Cross-section conversation cache
window._geoCounts;           // Geography data (country/state/city)
```

AI chat spend is stored in `localStorage` under key `buddees_usage` (written by the marketing site's chat widget):

```javascript
const usage = JSON.parse(localStorage.getItem('buddees_usage') || '{"tokens_in":0,"tokens_out":0,"cost":0,"conversations":0}');
```

---

## 5. Key Features - Implementation Details

### 5.1 Lead Scoring Engine

Every lead gets a 0-100 score based on behavioral signals:

```javascript
function scoreLead(lead, conversations, voiceCalls) {
  let score = 0;
  const signals = [];

  // Signal weights:
  // Corporate email:        +20
  // Voice Call lead:        +30
  // ROI Calculator used:    +20
  // Chat Interview:         +15
  // Footer Form:            +10
  // Multiple conversations: +10
  // Had voice call:         +15
  // CTA Converted:          +25
  // CTA Shown only:          +5
  // Location known:          +5
  // Recent (3 days):        +10

  // Cap at 100
  score = Math.min(100, score);
  const tier = score >= 60 ? 'hot' : score >= 25 ? 'warm' : 'cold';
  return { score, signals, tier, conversations: matchedConvos, voiceCalls: matchedVoice };
}
```

The scoring cross-references lead records against Conversations and Voice Calls tables by matching on email or name.

### 5.2 Sortable Columns

Uses event delegation on `th.sortable` elements:

```javascript
document.addEventListener('click', e => {
  const th = e.target.closest('th.sortable');
  if (!th) return;
  const key = th.dataset.sort;     // e.g., "score", "name", "date"
  const table = th.dataset.table;  // e.g., "leads", "roi-leads"

  // Toggle direction
  const wasAsc = th.classList.contains('sort-asc');
  // Clear siblings, set new direction
  // Call appropriate sort function
  if (table === 'leads') sortLeadsData();
  else if (table === 'roi-leads') sortROILeadsAndRender(key, dir);
});
```

HTML pattern:

```html
<th class="sortable" data-sort="score" data-table="leads">Score</th>
<th class="sortable" data-sort="name" data-table="leads">Name</th>
```

CSS indicators:

```css
th.sortable::after { content: ''; opacity: 0.35; }
th.sortable.sort-asc::after { content: ''; color: var(--accent-blue); }
th.sortable.sort-desc::after { content: ''; color: var(--accent-blue); }
```

### 5.3 Email Nurture System

4 pre-built templates + custom, sent via Resend API through `send-lead-email.php`:

| Template | Sender | Timing |
|----------|--------|--------|
| `welcome` | Tabby from Buddees | Immediate |
| `followup_48h` | Tabby from Buddees | 48 hours |
| `value_7d` | The Buddees Team | 7 days |
| `lastchance_14d` | Mark from Buddees | 14 days |
| `custom` | The Buddees Team | Any time |

**Individual send:**
```javascript
async function sendLeadEmail(template, leadData) {
  const resp = await fetch('/api/send-lead-email.php', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      template, name: leadData.name, email: leadData.email,
      trade: leadData.trade, business: leadData.business
    }),
  });
}
```

**Bulk send (rate-limited sequential):**
```javascript
async function bulkSendEmail(template) {
  const visible = /* currently filtered leads */;
  for (const lead of visible) {
    await sendLeadEmail(template, lead);
    await new Promise(r => setTimeout(r, 500)); // 500ms delay between sends
  }
}
```

### 5.4 Chart System

All charts use Chart.js with a chart instance management pattern to prevent memory leaks:

```javascript
let chartInstances = {};

function buildSomeChart(data) {
  const ctx = document.getElementById('chartId');
  // Destroy existing instance if re-rendering
  if (chartInstances['chartId']) chartInstances['chartId'].destroy();
  // Create new instance
  chartInstances['chartId'] = new Chart(ctx, { /* config */ });
}
```

Chart types used:
- **Bar charts:** Peak hours, agent totals
- **Line charts:** Agent trends (30-day), daily spend, growth velocity
- **Doughnut charts:** Traffic sources, agent spend breakdown, lead source
- **Custom HTML charts:** Conversion funnel (built with divs, not Chart.js), geography bars

Chart.js global theme settings used across all charts:

```javascript
// Common options pattern
{
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: 'rgba(255,255,255,0.05)' } },
    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } }
  }
}
```

### 5.5 Modal Pattern

Three modal types used throughout: Lead Detail, Session Detail, Transcript Viewer.

All follow the same pattern:

```html
<!-- Backdrop with click-to-close -->
<div id="modalId" style="display:none;position:fixed;inset:0;z-index:9999;
     background:rgba(0,0,0,0.7);backdrop-filter:blur(8px)"
     onclick="if(event.target===this)closeModal()">
  <!-- Modal card -->
  <div style="background:var(--bg-card);border:1px solid var(--border);
       border-radius:16px;width:90%;max-width:700px;max-height:85vh;
       display:flex;flex-direction:column;overflow:hidden">
    <!-- Header with title + close button -->
    <!-- Scrollable body -->
    <!-- Footer with action buttons -->
  </div>
</div>
```

Show/hide:
```javascript
function openModal() { document.getElementById('modalId').style.display = 'flex'; }
function closeModal() { document.getElementById('modalId').style.display = 'none'; }
```

### 5.6 Toast Notification System

```javascript
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<div class="toast-message">${message}</div>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
```

Types: `success` (green border), `error` (red border), `info` (blue border).

### 5.7 Follow-Up Alerts

Automated alerts generated from lead scoring:

```javascript
function buildFollowupAlerts(scoredLeads, conversations, voiceCalls) {
  const alerts = [];

  scoredLeads.forEach(lead => {
    // Hot lead not contacted in 1+ days
    if (lead.tier === 'hot' && lead.status === 'New' && daysSince >= 1)
      alerts.push({ type: 'hot-no-contact', priority: 1, ... });

    // Voice call lead with no follow-up
    if (lead.source === 'Voice Call' && lead.status === 'New')
      alerts.push({ type: 'voice-no-followup', priority: 2, ... });

    // CTA converted but still New
    if (lead.ctaConverted && lead.status === 'New')
      alerts.push({ type: 'cta-converted', priority: 1, ... });

    // Warm lead going cold (7+ days)
    if (lead.tier === 'warm' && lead.status === 'New' && daysSince >= 7)
      alerts.push({ type: 'going-cold', priority: 3, ... });
  });

  // Dedupe, sort by priority, show top 8
}
```

### 5.8 Sync / Refresh Pattern

```javascript
let lastSyncTime = null;

function updateSyncLabel() {
  const diffMin = Math.floor((Date.now() - lastSyncTime.getTime()) / 60000);
  if (diffMin < 1) syncEl.textContent = 'Synced just now';
  else syncEl.textContent = `Synced ${diffMin} min ago`;
}
setInterval(updateSyncLabel, 30000); // Update label every 30s

async function refreshAllData() {
  await loadAllData();  // Re-fetches everything
}
```

---

## 6. API Layer Reference

### 6.1 File Map

| File | Auth | Methods | Purpose |
|------|------|---------|---------|
| `_auth.php` | None / Self | GET, POST | Login, logout, check, elevate |
| `airtable.php` | Admin | GET, POST, PATCH | Full Airtable proxy (admin only) |
| `public-lead.php` | None (rate-limited) | POST, PATCH | Public lead writes with field allowlists |
| `send-lead-email.php` | Admin | POST | Nurture email sends via Resend |
| `openai.php` | Rate-limited | POST | OpenAI chat proxy (max 2000 tokens) |
| `stripe.php` | Rate-limited | POST | Create Stripe checkout sessions |
| `stripe-webhook.php` | Stripe signature | POST | Handle payment events |
| `send-registration-email.php` | Rate-limited | POST | Registration confirmation emails |
| `send-support-request.php` | Rate-limited | POST | Support ticket emails |
| `keys.php` | Admin | GET | Return non-secret publishable keys |
| `config.php` | N/A | N/A | Server-only secrets (gitignored) |

### 6.2 Config Pattern

```php
// config.php (gitignored, on server only)
define('OPENAI_API_KEY',    'sk-...');
define('AIRTABLE_TOKEN',    'pat...');
define('AIRTABLE_BASE_ID',  'app...');
define('RESEND_API_KEY',    're_...');
define('STRIPE_SECRET_KEY', 'sk_test_...');
define('STRIPE_WEBHOOK_SECRET', 'whsec_...');
define('BUDDEES_ADMIN_PASSWORD', '...');
define('BUDDEES_SUPER_ADMIN_PIN', '...');

// config.example.php (committed, has placeholders)
define('OPENAI_API_KEY', getenv('OPENAI_API_KEY') ?: 'sk-YOUR_KEY_HERE');
```

### 6.3 CORS Configuration

All endpoints restrict CORS to same-origin:

```php
$allowedOrigins = ['https://buddees.ai', 'https://www.buddees.ai'];
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (in_array($origin, $allowedOrigins)) {
  header('Access-Control-Allow-Origin: ' . $origin);
}
// Admin endpoints also add:
header('Access-Control-Allow-Credentials: true');
```

### 6.4 .htaccess Protection

```apache
<FilesMatch "(config\.php|config\.example\.php|_rate_limit_cache)">
    Order Allow,Deny
    Deny from all
</FilesMatch>
Options -Indexes
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteRule ^_rate_limit_cache/ - [F,L]
</IfModule>
```

---

## 7. Stripe Integration

### 7.1 Webhook Verification

```php
// Parse Stripe-Signature header
$sigParts = []; // Extract t= and v1= values
$timestamp = $sigParts['t'];
$signature = $sigParts['v1'];

// Reject replay attacks (5 minute window)
if (abs(time() - intval($timestamp)) > 300) { /* reject */ }

// Compute and compare HMAC
$signedPayload = $timestamp . '.' . $payload;
$expected = hash_hmac('sha256', $signedPayload, STRIPE_WEBHOOK_SECRET);
if (!hash_equals($expected, $signature)) { /* reject */ }
```

### 7.2 Handled Events

- `checkout.session.completed` - Logs payment to Airtable Early Access table
- `invoice.payment_failed` - Logs failed payment for follow-up

---

## 8. Replication Checklist

To replicate this architecture for a new project:

### 8.1 Frontend (admin.html)

1. Copy the CSS variable system (section 2.2) and adapt colors
2. Implement the sidebar + topbar + main-wrapper layout (section 2.3)
3. Create section elements for each page with the tab switching pattern (section 2.4)
4. Add Chart.js via CDN
5. Implement the `fetchAirtable()` function with pagination (section 4.3)
6. Build stat cards using the `.stat-card` pattern with `countUp()` animation
7. Implement the chart instance management pattern (section 5.4)
8. Add the modal pattern for drill-downs (section 5.5)
9. Add the toast notification system (section 5.6)
10. Implement sortable columns with event delegation (section 5.2)

### 8.2 Backend (api/ directory)

1. Create `config.php` and `config.example.php` with your secrets
2. Implement `_auth.php` with session-based auth and rate limiting
3. Create your admin-only data proxy (like `airtable.php`)
4. Create your public write proxy with field allowlists (like `public-lead.php`)
5. Add `.htaccess` to protect config and cache files
6. Set up email sending via Resend or your preferred provider
7. Add Stripe webhook handling if needed

### 8.3 Hosting

- GoDaddy shared hosting (or any PHP host)
- GitHub Actions with FTP-Deploy-Action for CI/CD
- `config.php` stays gitignored, manually uploaded to server

### 8.4 Airtable Setup

1. Create your base with the required tables
2. Generate a Personal Access Token (PAT)
3. Define your table schema to match what the frontend expects
4. The proxy pattern means you can swap Airtable for any API (Supabase, Firebase, etc.) by changing only the proxy files

---

## 9. Key Patterns to Reuse

### Pattern: Animated Stat Card

```html
<div class="stat-card" style="animation-delay: 0.1s;">
  <div class="stat-label">METRIC NAME</div>
  <div class="stat-value" data-target="metric-id">0</div>
  <div class="stat-change"><span class="change-badge change-up">+12%</span></div>
</div>
```

### Pattern: Filterable Table with Search

```html
<input type="text" onkeyup="filterItems(this.value)">
<select onchange="filterByStatus(this.value)">
  <option value="">All</option>
  <option value="Active">Active</option>
</select>
<button onclick="exportCSV()">Export CSV</button>
```

### Pattern: Week-over-Week Change Badge

```javascript
const setBadge = (selector, thisWeek, lastWeek) => {
  const pct = Math.round(((thisWeek - lastWeek) / lastWeek) * 100);
  const cls = pct >= 0 ? 'change-up' : 'change-down';
  el.innerHTML = `<span class="change-badge ${cls}">${pct >= 0 ? '+' : ''}${pct}%</span> vs last week`;
};
```

### Pattern: Conversion Funnel (HTML, not Chart.js)

```javascript
const funnelSteps = [
  { label: 'Step 1', value: 1000, color: '#0066FF' },
  { label: 'Step 2', value: 500, color: '#FFB400' },
  { label: 'Step 3', value: 100, color: '#34D399' },
];
const funnelMax = Math.max(...funnelSteps.map(s => s.value), 1);
// Render as proportional-height divs
```

### Pattern: Geography Bar Chart (HTML, not Chart.js)

```javascript
const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0,10);
sorted.map(([name, count]) => {
  const pct = Math.round((count / max) * 100);
  return `<div style="width:${pct}%;height:6px;background:gradient;..."></div>`;
});
```

---

## 10. Security Summary

| Control | Implementation |
|---------|---------------|
| Auth | Server-side PHP sessions, HttpOnly/Secure/SameSite=Strict cookies |
| Secrets | config.php gitignored, no secrets in client JS |
| CORS | Allowlisted origins only, no wildcard `*` |
| Rate limiting | File-based per-IP, configurable per endpoint |
| Input validation | Field allowlists, string truncation, type checking |
| Error handling | `display_errors = 0` in production, errors logged server-side |
| Webhook security | Stripe HMAC-SHA256 signature verification with timestamp replay protection |
| Super admin | Separate password for destructive actions |
| Session fixation | `session_regenerate_id(true)` on login |

---

## 11. File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| `admin.html` | ~4,800 | Full SPA (CSS + HTML + JS) |
| `_auth.php` | ~167 | Auth + rate limiting |
| `airtable.php` | ~64 | Admin data proxy |
| `public-lead.php` | ~136 | Public write proxy |
| `send-lead-email.php` | ~284 | Email nurture (4 templates) |
| `stripe-webhook.php` | ~132 | Payment event handler |
| `config.php` | ~26 | Secrets |

Total backend: approximately 800 lines of PHP.
Total frontend: approximately 4,800 lines of HTML/CSS/JS.

---

*This document is a complete reference for replicating the admin console architecture. For the actual codebase, see the files at `buddees.ai/admin.html` and `buddees.ai/api/`.*
