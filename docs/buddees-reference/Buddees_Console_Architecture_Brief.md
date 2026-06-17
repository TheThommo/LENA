# Buddees Console Architecture Brief

**Purpose:** Technical reference for replicating the HQ + Support console pattern in another project.
**Date:** June 17, 2026
**Stack:** Vite + React + TypeScript + Supabase + Railway

---

## 1. The Big Picture

One static SPA serves every subdomain. A wildcard DNS record (`*.buddees.app`) points to a single Railway deployment. The app reads `window.location.hostname` at boot and decides what to render:

```
*.buddees.app (wildcard DNS -> Railway)
    |
    +-- hq.buddees.app        -> HQ Console (CEO control tower)
    +-- support.buddees.app   -> Support Console (customer ops)
    +-- app.buddees.app       -> Central login / default app
    +-- {company}.buddees.app -> Tenant app
```

There is no separate build per console. It is the same JS bundle everywhere. Routing is 100% client-side.

---

## 2. Subdomain Detection

### 2.1 The Core Function

**File:** `apps/web/src/stores/tenant-context.ts` (lines 44-81)

```typescript
function extractSubdomain(): string | null {
  const hostname = window.location.hostname;

  // Dev: {slug}.localhost
  if (hostname.endsWith('.localhost')) {
    const slug = hostname.replace('.localhost', '');
    if (!slug || slug === 'localhost') return null;
    return slug;
  }

  // Skip bare localhost / 127.0.0.1
  if (hostname === 'localhost' || hostname === '127.0.0.1') return null;

  // Production: need >= 3 parts (slug.buddees.app)
  const parts = hostname.split('.');
  if (parts.length < 3) return null;

  const slug = parts[0];
  const reserved = [
    'www', 'app', 'api', 'admin', 'staging', 'dev',
    'mail', 'hq', 'console', 'help', 'support', 'docs'
  ];

  if (reserved.includes(slug)) return null;
  return slug;
}
```

Reserved subdomains return `null` (not a tenant). Everything else is a tenant slug.

### 2.2 Console Host Checkers

Two simple functions determine which console mode we're in:

**File:** `apps/web/src/lib/consolePermissions.ts` (line 155)
```typescript
export function isConsoleHost(hostname: string): boolean {
  return hostname === 'hq.buddees.app' || hostname === 'hq.localhost';
}
```

**File:** `apps/web/src/lib/supportPermissions.ts` (line 14)
```typescript
export function isSupportHost(hostname: string): boolean {
  return hostname === 'support.buddees.app' || hostname === 'support.localhost';
}
```

### 2.3 The Decision Tree

```
window.location.hostname
  |
  +-- hq.buddees.app / hq.localhost
  |     extractSubdomain() = null (reserved)
  |     isConsoleHost() = true
  |     SmartLanding -> /console
  |     Tenant routes -> redirect to /console
  |     ConsoleLayout enforces canAccessConsole()
  |
  +-- support.buddees.app / support.localhost
  |     extractSubdomain() = null (reserved)
  |     isSupportHost() = true
  |     SmartLanding -> /support
  |     Tenant routes -> redirect to /support
  |     SupportLayout enforces canAccessSupport()
  |
  +-- app.buddees.app
  |     extractSubdomain() = null (reserved)
  |     Central app: may redirect to {slug}.buddees.app
  |     based on tenant.central_app_login flag
  |
  +-- {slug}.buddees.app (non-reserved)
  |     extractSubdomain() = "slug"
  |     Resolves tenant via Supabase query
  |     Not found -> TenantNotFoundPage
  |     Found -> normal tenant app
  |
  +-- buddees.ai / buddees.app / www.*
        Post-auth: always redirects to {slug}.buddees.app
```

---

## 3. Router Architecture

**File:** `apps/web/src/App.tsx`

One single `BrowserRouter`. Console and support routes live alongside tenant routes. The trick: the parent layout elements redirect based on hostname, so tenant pages never render on console hosts and vice versa.

### 3.1 Boot Sequence (lines 259-300)

1. `resolveFromHostname()` runs first (tenant context store)
2. Once resolved, `initialize()` runs (auth store)
3. If on a tenant subdomain and tenant not found, render `<TenantNotFoundPage />`

### 3.2 SmartLanding Component (lines 232-257)

The `/` route uses hostname to redirect:
- `isConsoleHost()` -> `/console`
- `isSupportHost()` -> `/support`
- Otherwise, permission-based redirect to `/dashboard`, `/workspace`, etc.

### 3.3 Route Structure (lines 302-516)

```
/auth/*                    -> Auth pages (login, register, etc.) - always available
/proposals/view/:token     -> Public (no auth)
/onboarding                -> Protected, no sidebar

/workspace                 -> if isConsoleHost: redirect to /console
                              if isSupportHost: redirect to /support
                              else: WorkspacePage

/* (tenant app routes)     -> Parent element checks:
                              isConsoleHost ? Navigate(/console) :
                              isSupportHost ? Navigate(/support) :
                              <AppLayout />

/console/*                 -> <ConsoleLayout> wraps all HQ pages
/support/*                 -> <SupportLayout> wraps all Support pages
```

### 3.4 Lazy Loading

All console and support pages are lazy-loaded:

```typescript
const CommandCenterPage = lazy(() => import('./pages/console/CommandCenterPage'));
const SupportHomePage = lazy(() => import('./pages/support/SupportHomePage'));
// ... etc
```

---

## 4. Authentication and Authorization

### 4.1 Cross-Subdomain Sessions

**File:** `apps/web/src/lib/cross-subdomain-storage.ts`

Sessions are stored in cookies scoped to `.buddees.app` (the parent domain). This means a user logged in on `app.buddees.app` is automatically authenticated on `hq.buddees.app` and `support.buddees.app`. The implementation chunks cookies to handle the 4KB browser limit since Supabase sessions can be larger.

**File:** `apps/web/src/lib/supabase.ts`

The Supabase client is configured with the `crossSubdomainStorage` adapter instead of default localStorage.

### 4.2 Platform Roles

**Type definition** (`apps/web/src/types/index.ts` line 11):
```typescript
export type PlatformRole = 'platform_owner' | 'ceo_view' | 'administrator' | 'support';
```

**Role loading** (`apps/web/src/stores/auth.ts` lines 614-646):
`loadPlatformRole()` queries `platform_role_assignments` joined with `roles(name)` for the authenticated user.

**DB table:** `platform_role_assignments` with columns `user_id`, `role_id`, linking to the `roles` table.

### 4.3 HQ Access Control

**File:** `apps/web/src/lib/consolePermissions.ts`

```typescript
// Gate: who can see the console at all
canAccessConsole(platformRole, tenantRole):
  platformRole in ['platform_owner', 'ceo_view', 'administrator', 'support']
  OR tenantRole === 'super_admin'

// Granular permissions (functions, not a matrix)
canViewFinancials()       -> platform_owner | ceo_view | super_admin
canWriteTenants()         -> platform_owner | administrator | super_admin
canImpersonate()          -> platform_owner | administrator | super_admin
canResetPasswords()       -> platform_owner | administrator | support | super_admin
canEditPlaybooks()        -> platform_owner | administrator | super_admin
canViewAuditLog()         -> platform_owner | administrator | super_admin
canManagePlatformRoles()  -> platform_owner only
canEditBusinessGoals()    -> platform_owner | super_admin
canExportInvestorPack()   -> platform_owner | ceo_view | super_admin
```

**Nav visibility** is controlled by `consoleNav()` which returns a `ConsoleNavVisibility` object. Each nav item checks a key in that object. Example: `support` role sees Ops, Alerts, Tenants, Users, Agent Failures but NOT Financial, CEO, Growth, Goals, Investor.

### 4.4 Support Access Control

**File:** `apps/web/src/lib/supportPermissions.ts`

```typescript
canAccessSupport(platformRole, tenantRole):
  platformRole in ['platform_owner', 'administrator', 'support']
  OR tenantRole === 'super_admin'

canImpersonateFromSupport():
  platform_owner | administrator | super_admin
  // 'support' role is EXCLUDED from impersonation
```

### 4.5 Enforcement Pattern

Both console layouts follow the same pattern in their inner component:

```typescript
// Inside ConsoleLayoutInner / SupportLayoutInner
if (isLoading) return <Spinner />;
if (!isAuthenticated) return <Navigate to="/auth/login" state={{ from: location }} />;
if (!canAccessConsole(platformRole, tenantRole)) return <Navigate to="/dashboard" />;
```

---

## 5. Console Layouts

### 5.1 HQ Console Layout

**File:** `apps/web/src/pages/console/ConsoleLayout.tsx`

**Structure:** 3-column CSS Grid

```
+------------------+------------------------+------------------+
|    Left Nav      |      Main Content      |   Activity Rail  |
|    (210px)       |        (1fr)           |     (360px)      |
|                  |                        |                  |
| Logo + "HQ"     | Demo toggle toolbar    | Month So Far     |
| Nav groups:      | Demo banner (if on)    | Top Tenants      |
|  - Overview      | <Outlet />             | Billing Activity |
|  - Revenue       |                        | Suggested Actions|
|  - Operations    |                        |                  |
|  - People        |                        |                  |
|  - Strategy      |                        |                  |
|  - Governance    |                        |                  |
| User footer      |                        |                  |
| Theme toggle     |                        |                  |
+------------------+------------------------+------------------+
```

**Wrapping context providers:**
```typescript
<ConsoleThemeProvider variant="hq">
  <DrillDownProvider>
    <ConsoleLayoutInner />
  </DrillDownProvider>
</ConsoleThemeProvider>
```

**CSS injection:** Styles are injected into `<head>` via `ensureShellStyles()` using a `<style id="hq-shell-styles">` tag. This avoids Tailwind class collisions and gives precise control.

**Responsive breakpoints:**

| Width | Behavior |
|---|---|
| >1440px | Full 3-column: 210px / 1fr / 360px |
| 1440px | Narrow: 200px / 1fr / 320px |
| 1366px | Nav collapses to 60px icon-only rail (iPad Pro landscape). Tooltips on hover. |
| 1180px | 56px / 1fr / 300px |
| 1024px | Rail drops below main as 2-column grid (iPad portrait) |
| 720px | Single column, nav becomes off-canvas drawer (phone) |

### 5.2 Support Console Layout

**File:** `apps/web/src/pages/support/SupportLayout.tsx`

**Structure:** 2-column CSS Grid (no activity rail)

```
+------------------+--------------------------------------+
|    Left Nav      |           Main Content               |
|    (220px)       |             (1fr)                    |
|                  |                                      |
| "S" logo (teal)  | <Outlet />                          |
| Nav groups:      |                                      |
|  - Operations    |                                      |
|  - Directory     |                                      |
|  - Agent Ops     |                                      |
|  - Governance    |                                      |
| User footer      |                                      |
| Theme toggle     |                                      |
+------------------+--------------------------------------+
```

**Same wrapping pattern:**
```typescript
<ConsoleThemeProvider variant="support">
  <DrillDownProvider>
    <SupportLayoutInner />
  </DrillDownProvider>
</ConsoleThemeProvider>
```

**Same responsive ladder** with class prefix `sp-` instead of `hq-`.

---

## 6. Theme System

### 6.1 Architecture

**File:** `apps/web/src/lib/console-theme.ts`

Token-driven theming. No CSS variables, no CSS-in-JS. All styling via inline `style={{}}` props consuming theme tokens. The theme object (`T`) is accessed via `useConsoleTheme()` hook.

Two dimensions:
- **Variant:** `'hq'` (red accent) or `'support'` (teal accent)
- **Mode:** `'dark'` or `'light'`

```typescript
// Usage in any console page
const T = useConsoleTheme();
return <div style={{ background: T.surface.base, color: T.text.primary }}>...</div>;
```

### 6.2 Token Structure

```typescript
{
  surface: {
    base:     string,  // Deepest background
    elevated: string,  // Cards, panels
    raised:   string,  // Hover states, active items
    overlay:  string,  // Modals, dropdowns
  },
  text: {
    primary:   string,  // Main content
    secondary: string,  // Labels, descriptions
    tertiary:  string,  // Timestamps, metadata
    muted:     string,  // Disabled, placeholders
    inverse:   string,  // Text on colored backgrounds
  },
  line: {
    hairline: string,  // 4% opacity borders
    subtle:   string,  // 8% opacity
    strong:   string,  // 14% opacity
  },
  brand: {
    primary:     string,  // HQ: #E53116 (red) | Support: #0EA5E9 (teal)
    primarySoft: string,  // rgba variant for backgrounds
    primaryDim:  string,  // Muted variant
  },
  semantic: {
    success:     string,  // Green
    successSoft: string,
    warning:     string,  // Amber
    warningSoft: string,
    danger:      string,  // Red
    dangerSoft:  string,
    info:        string,  // Blue
    infoSoft:    string,
  },
  typography: {
    display:  { size: '34px', weight: 700, tracking: '-0.02em' },
    title:    { size: '20px', weight: 600, tracking: '-0.01em' },
    heading:  { size: '14px', weight: 600, tracking: '0' },
    body:     { size: '12px', weight: 400, tracking: '0' },
    caption:  { size: '11px', weight: 400, tracking: '0.01em' },
    label:    { size: '10px', weight: 600, tracking: '0.06em' },
    micro:    { size: '9px',  weight: 500, tracking: '0.04em' },
  },
  shadow: {
    low:    string,  // Subtle elevation
    medium: string,  // Cards
    high:   string,  // Modals
    inner:  string,  // Inset
  },
  radius: {
    sm: '8px', md: '12px', lg: '16px', xl: '24px', pill: '9999px'
  },
  fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif"
}
```

### 6.3 Mode Persistence

- Stored in `localStorage` under key `buddees.hq.theme`
- A `data-hq-theme` attribute is set on `document.documentElement`
- Light mode injects CSS overrides to remap Tailwind dark-text classes

### 6.4 Design Philosophy

Brand color is used "like salt, not sugar." The accent (red for HQ, teal for Support) appears only in:
- Active nav item indicator
- KPI trend arrows
- Status badges
- Primary action buttons
- The logo mark

Everything else is neutral grayscale surfaces with subtle borders.

---

## 7. Shared UI Components

### 7.1 Console Primitives

**File:** `apps/web/src/components/console/primitives.tsx`

Shared between HQ and Support. All components consume theme tokens via `useConsoleTheme()`.

| Component | Purpose |
|---|---|
| `PageHeader` | Page title + optional subtitle, actions slot |
| `Card` | Elevated surface container with padding and radius |
| `StatTile` | Single metric with label, value, trend indicator |
| `Sparkline` | Inline SVG mini chart |
| `AreaChart` | Filled area chart |
| `DataRow` | Label-value pair row |
| `EmptyState` | Centered icon + message for empty data |
| `Badge` | Status pill (semantic colors) |
| `WindowSelector` | Time window picker (7d / 30d / 90d) |
| `Grid` | CSS grid wrapper with responsive columns |
| `KpiRow` | Horizontal row of KPI tiles |
| `Kpi` | Single KPI card with value, label, trend |
| `Tabs` | Tab bar with content switching |

### 7.2 DrillDown Drawer

**File:** `apps/web/src/components/console/DrillDownDrawer.tsx`

A 480px slide-in panel from the right edge. Used in both consoles for detail views without leaving the list page.

**Provider pattern:**
```typescript
<DrillDownProvider>
  {/* Pages can call drill.open() / drill.close() */}
</DrillDownProvider>
```

**Opening:**
```typescript
const drill = useDrillDown();
drill.open({
  crumb: 'User Detail',
  title: user.name,
  sub: user.email,
  body: <UserDetailContent user={user} />
});
```

**Sub-components for drawer body:**

| Component | Purpose |
|---|---|
| `DrawerHero` | Top section with avatar/icon + title |
| `DrawerSectionLabel` | Section divider with label |
| `DrawerTable` | Table inside drawer |
| `DrawerRow` | Key-value row |
| `DrawerAvatar` | User avatar circle |
| `DrawerNote` | Timestamped note/comment |
| `DrawerMiniSpark` | Inline sparkline in drawer |

**Animation:** cubic-bezier slide + backdrop blur. Escape key and backdrop click close the drawer.

### 7.3 Activity Rail (HQ only)

**File:** `apps/web/src/components/console/ActivityRail.tsx`

The right column of the HQ layout showing:
- Month So Far stats
- Top Tenants by MRR
- Billing Activity timeline
- Suggested Actions

Respects `demoMode` prop for data source switching.

---

## 8. Data Layer

### 8.1 Pattern

All console data comes from Supabase RPCs. Each RPC is a `SECURITY DEFINER` function gated server-side (only callable by users with the right platform role). Pages call RPCs directly via the Supabase client, no intermediate API layer.

```typescript
const { data, error } = await supabase.rpc('get_platform_kpis');
```

### 8.2 HQ Console RPCs (22 total)

| RPC | Used by | Purpose |
|---|---|---|
| `get_platform_kpis` | CommandCenter, CEO, InvestorPack | Headline KPIs: tenant counts, growth, MRR/ARR, trial funnel |
| `get_recent_tenants` | CommandCenter | Latest 8 tenants with subscription info |
| `get_tier_distribution` | CEO | Tenants + MRR per plan tier |
| `get_buddees_revenue_summary` | FinancialOps | MRR by tier (param: `p_window_days`) |
| `get_voice_cost_summary` | FinancialOps | Voice/call cost breakdown |
| `get_growth_summary` | Growth, InvestorPack | Growth pipeline (param: `p_window_days`) |
| `get_country_intelligence` | Growth | Tenant distribution by country |
| `get_product_health` | ProductHealth | Feature adoption, conversation volumes |
| `get_ops_health` | OpsHealth | Service uptime, infra metrics |
| `get_active_alerts` | Alerts | Open alert queue with priorities |
| `get_tenant_universe` | TenantsList | All tenants + subscription + activity |
| `get_tenant_detail` | TenantDetail | Single tenant deep-dive |
| `get_platform_pulse` | PlatformPulse | Live user activity from heartbeats |
| `get_platform_buddle_console_stats` | BuddleConsole | Cross-tenant group chat stats |
| `search_users_across_tenants` | Users | Cross-tenant user search |
| `get_playbook_library` | PlaybookLibrary | Global playbook CRUD |
| `get_audit_actors` | AuditLog | Actor list for filtering |
| `get_audit_log_page` | AuditLog | Paginated audit entries |
| `list_business_objectives` | BusinessGoals | OKR list |
| `upsert_objective` | BusinessGoals | Create/update objective |
| `upsert_key_result` | BusinessGoals | Create/update key result |
| `delete_objective` / `delete_key_result` | BusinessGoals | Remove OKR items |

Direct table queries: `AgentFailuresPage` reads `agent_failure_log` via `platform_read_all` RLS policy. `SubscriptionsPage` and `InvoicesPage` also query tables directly.

### 8.3 Support Console RPCs (24 total)

**Read RPCs (16):**

| RPC | Purpose |
|---|---|
| `support_search_users` | Search users by name/email |
| `support_get_user_detail` | User detail with memberships |
| `support_search_tenants` | Search tenants by name/slug |
| `support_list_tenant_members` | List members of a tenant |
| `support_get_tenant_360` | Comprehensive tenant view |
| `support_get_tenant_config` | Tenant configuration |
| `support_list_recent_actions` | Audit log feed |
| `support_trial_followup_health` | Trial health metrics |
| `support_get_escalation_queue` | Cross-tenant escalation queue |
| `support_list_billing_overview` | Billing summary + tenant list |
| `support_agent_health_overview` | Agent health metrics |
| `support_agent_failures` | Agent failure details |
| `support_kb_browse` | KB entries for a tenant |
| `support_get_tenant_conversations` | Conversations for a tenant |
| `support_get_conversation_messages` | Message thread |
| `support_list_impersonation_history` | Impersonation audit trail |

**Write RPCs (8):**

| RPC | Purpose |
|---|---|
| `support_log_password_reset` | Log + trigger password reset |
| `support_extend_trial` | Adjust tenant trial period |
| `support_log_impersonation` | Log impersonation session |
| `support_log_billing_action` | Log billing credit/refund |
| `support_update_tenant_config` | Update tenant config |
| `support_suspend_tenant` | Suspend/restore tenant |
| `support_toggle_user_active` | Toggle user active/inactive |
| `support_send_notification` | Send notification to user |

---

## 9. State Management

### 9.1 Global Stores (Zustand)

| Store | File | Console Usage |
|---|---|---|
| `useAuthStore` | `stores/auth.ts` | Session, user, platformRole, memberships, signIn/signOut |
| `useTenantContext` | `stores/tenant-context.ts` | Subdomain resolution (returns null for reserved hosts) |
| `useImpersonationStore` | `stores/impersonation.ts` | Impersonation session tracking |

### 9.2 Context Providers

| Context | Provider | Provides |
|---|---|---|
| Console Theme | `ConsoleThemeProvider` | Theme tokens (T), mode, toggle function |
| Drill Down | `DrillDownProvider` | open/close drawer, current content |
| Console Context | React Router `<Outlet context>` | `{ demoMode: boolean }` (HQ only) |

### 9.3 Page-Level State

No global HQ or Support data cache. Each page manages its own `useState` for data, loading, and errors. Pages fetch independently on mount.

---

## 10. HQ Console Pages (23 total)

**Directory:** `apps/web/src/pages/console/`

| Route | Component | Purpose |
|---|---|---|
| `/console` | `CommandCenterPage` | State-of-business: 5 KPI tiles, pulse chart, top tenants, alert stream |
| `/console/ceo` | `CEODashboardPage` | Investor KPIs: MRR/ARR, tenant pie chart, trial funnel, growth |
| `/console/financial` | `FinancialOpsPage` | Revenue deep-dive: MRR by tier, voice costs, demo/live toggle |
| `/console/subscriptions` | `SubscriptionsPage` | Cross-tenant subscription list |
| `/console/invoices` | `InvoicesPage` | Cross-tenant invoice list |
| `/console/growth` | `GrowthPage` | Growth pipeline, country intelligence |
| `/console/product` | `ProductHealthPage` | Feature adoption, conversation volumes |
| `/console/ops` | `OpsHealthPage` | Service uptime, latency, infra health |
| `/console/alerts` | `AlertsPage` | Active alert triage queue (P1/P2/P3) |
| `/console/agent-failures` | `AgentFailuresPage` | Agent failure log triage |
| `/console/tenants` | `TenantsListPage` | Full tenant universe with search/filter |
| `/console/tenants/:tenantId` | `TenantDetailPage` | Tenant deep-dive |
| `/console/support` | `SupportPanelPage` | In-console support tools |
| `/console/playbooks` | `PlaybookLibraryPage` | Global playbook CRUD |
| `/console/audit` | `AuditLogPage` | Compliance audit trail with actor filtering |
| `/console/goals` | `BusinessGoalsPage` | OKR management |
| `/console/investor` | `InvestorPackPage` | Investor-ready data export |
| `/console/users` | `UsersPage` | Cross-tenant user directory |
| `/console/pulse` | `PlatformPulsePage` | Live user activity, engagement leaderboard |
| `/console/buddle` | `BuddleConsolePage` | Group chat monitoring |
| `/console/settings` | `ConsoleSettingsPage` | Placeholder for role management, MFA, branding |

---

## 11. Support Console Pages (15 total)

**Directory:** `apps/web/src/pages/support/`

| Route | Component | Purpose |
|---|---|---|
| `/support` | `SupportHomePage` | Dashboard: KPIs, ticket queue, trial health, activity feed |
| `/support/users[/:userId]` | `SupportUsersPage` | User search + drill-down drawer (password reset) |
| `/support/tenants[/:tenantId]` | `SupportTenantsPage` | Tenant search + drill-down drawer (trial adjust) |
| `/support/tenants/:id/360` | `SupportTenant360Page` | Full-page tenant deep-dive |
| `/support/tenants/:id/conversations/:cid` | `SupportConversationInspectorPage` | Message thread viewer |
| `/support/audit` | `SupportAuditLogPage` | Filterable audit log |
| `/support/impersonate` | `SupportImpersonatePage` | 3-step wizard: select tenant, user, reason, launch |
| `/support/escalations` | `SupportEscalationQueuePage` | Priority queue: escalated convos, pending approvals |
| `/support/billing` | `SupportBillingPage` | Billing overview with per-tenant actions |
| `/support/agents` | `SupportAgentHealthPage` | Agent health: failure rates, task success |
| `/support/kb` | `SupportKBInspectorPage` | Browse KB entries per tenant |
| `/support/tenant-ops` | `SupportTenantOpsPage` | Tenant config, suspend/restore |
| `/support/user-ops` | `SupportUserOpsPage` | User operations: toggle active, send notifications |
| `/support/flags` | `SupportFeatureFlagsPage` | Per-tenant feature flag management |
| `/support/*` | `SupportComingSoonPage` | Catch-all placeholder |

---

## 12. Demo Mode (HQ only)

### How It Works

1. **Build-time default:** `VITE_HQ_DEMO_MODE` env var (defaults to `'true'`)
2. **Runtime toggle:** Users flip a pill in the toolbar. Persists to `localStorage` under `buddees.hq.demoMode`
3. **Flow:** `ConsoleLayoutInner` reads stored preference, passes `demoMode` boolean via React Router's `<Outlet context={{ demoMode }} />`
4. **Consumption:** Pages call `useConsoleContext()` to get `{ demoMode }`
5. **Data handling:** `console-demo-data.ts` exports seeded data. `mergeLiveAndDemo()` checks if the RPC returns `is_demo_data: true` and overlays seeded numbers while preserving real values

**Visual indicators when demo is active:**
- Yellow banner: "Demo mode active. Numbers below are seeded."
- "Demo Data" badge next to page title
- Toggle pill shows amber "DEMO ON" vs green "LIVE OFF"

---

## 13. Impersonation

### The Flow

1. Support user on `SupportImpersonatePage` selects tenant, user, provides mandatory reason
2. `support_log_impersonation` RPC writes to `support_actions` audit table
3. Opens `https://{slug}.buddees.app/dashboard?impersonate=1` in a new tab
4. Auth store detects `?impersonate=1`, synthesizes a membership for the target tenant
5. `ImpersonationBanner` renders: red sticky bar + "Read Only" badge
6. `useRedHalo()` hook injects a pulsing red `box-shadow` around the entire viewport
7. "Exit" button redirects back to `support.buddees.app/impersonate`

### Permission

Only `platform_owner`, `administrator`, or `super_admin` can impersonate. The `support` platform role is explicitly excluded.

### Shared Component

**File:** `apps/web/src/components/shared/ImpersonationBanner.tsx`

Renders in both console layouts and the tenant app layout when impersonation is active.

---

## 14. Detail View Patterns

### Pattern A: Drill-Down Drawer

Used by: Users page, Tenants page (both consoles)

1. List page renders searchable table
2. Click row -> URL updates to include ID (`/support/users/:userId`)
3. `useEffect` watching URL param fetches detail RPC
4. Result passed to `drill.open({ crumb, title, sub, body })`
5. 480px drawer slides in from right with blurred backdrop
6. Close via Escape, backdrop click, or close button
7. URL navigates back to list

### Pattern B: Full Page

Used by: Tenant360, ConversationInspector, all ops pages

1. Navigate to dedicated route
2. Full page renders with back link at top
3. Uses `PageHeader`, `Card`, `KpiRow`, `DataRow` primitives
4. Two-column grid (2fr + 1fr) for dense info

### Pattern C: Modal Dialog

Used by: Password reset, trial extension, billing actions

1. Fixed-position modal with `rgba(0,0,0,0.6)` overlay
2. Centered card on theme surface
3. Mandatory reason field (min 5 chars) for destructive actions
4. Success flash after completion

---

## 15. Key File Map

### Infrastructure
```
apps/web/src/App.tsx                              # All route definitions
apps/web/src/stores/tenant-context.ts             # Subdomain detection + resolution
apps/web/src/stores/auth.ts                       # Auth, platformRole, session sharing
apps/web/src/stores/impersonation.ts              # Impersonation state
apps/web/src/lib/supabase.ts                      # Supabase client
apps/web/src/lib/cross-subdomain-storage.ts       # Cookie-based session sharing
apps/web/src/types/index.ts                       # PlatformRole type
```

### HQ Console
```
apps/web/src/pages/console/ConsoleLayout.tsx       # Shell (3-col grid, nav, rail)
apps/web/src/pages/console/CommandCenterPage.tsx   # Landing page
apps/web/src/pages/console/CEODashboardPage.tsx    # Investor KPIs
apps/web/src/pages/console/FinancialOpsPage.tsx    # Revenue deep-dive
apps/web/src/pages/console/TenantsListPage.tsx     # Tenant universe
apps/web/src/pages/console/TenantDetailPage.tsx    # Tenant detail
apps/web/src/pages/console/UsersPage.tsx           # Cross-tenant user directory
apps/web/src/pages/console/ConsoleSettingsPage.tsx # Settings (placeholder)
apps/web/src/pages/console/*.tsx                   # All other HQ pages
apps/web/src/lib/consolePermissions.ts             # HQ permissions + nav visibility
apps/web/src/lib/console-demo-data.ts              # Seeded demo data
```

### Support Console
```
apps/web/src/pages/support/SupportLayout.tsx       # Shell (2-col grid, nav)
apps/web/src/pages/support/SupportHomePage.tsx      # Dashboard
apps/web/src/pages/support/SupportUsersPage.tsx     # User search + drawer
apps/web/src/pages/support/SupportTenantsPage.tsx   # Tenant search + drawer
apps/web/src/pages/support/SupportTenant360Page.tsx # Tenant 360 full page
apps/web/src/pages/support/*.tsx                    # All other Support pages
apps/web/src/lib/supportPermissions.ts              # Support permissions + nav visibility
```

### Shared Components
```
apps/web/src/components/console/primitives.tsx      # PageHeader, Card, Badge, Kpi, etc.
apps/web/src/components/console/DrillDownDrawer.tsx  # 480px slide-in drawer
apps/web/src/components/console/ActivityRail.tsx     # HQ right rail
apps/web/src/components/shared/ImpersonationBanner.tsx
apps/web/src/lib/console-theme.ts                    # Theme tokens (both variants)
apps/web/src/lib/useConsoleTheme.tsx                  # Theme provider + hooks
```

---

## 16. Replication Checklist

To replicate this pattern in another project:

1. **DNS:** Set up wildcard `*.yourdomain.com` CNAME to your hosting provider
2. **Single SPA:** Deploy one static build that serves all subdomains
3. **Subdomain extractor:** Port `extractSubdomain()` with your reserved list
4. **Host checkers:** Create `isAdminHost()` / `isSupportHost()` functions
5. **Router guards:** In the parent route element, redirect based on hostname
6. **SmartLanding:** Redirect `/` based on which host the user is on
7. **Cross-subdomain auth:** Use cookies scoped to the parent domain (`.yourdomain.com`)
8. **Platform roles table:** `platform_role_assignments` linking users to roles
9. **Permission functions:** One file per console with granular checks
10. **Layout shell:** CSS grid injected via `<style>` tag, responsive breakpoint ladder
11. **Theme system:** Token objects consumed via React context, inline styles
12. **Console primitives:** Build the shared component kit (PageHeader, Card, Kpi, DrillDown, etc.)
13. **RPCs:** Supabase `SECURITY DEFINER` functions for cross-tenant data access
14. **Lazy loading:** `lazy(() => import(...))` all console pages
15. **Demo mode:** Env var default + localStorage override + Outlet context pass-through
