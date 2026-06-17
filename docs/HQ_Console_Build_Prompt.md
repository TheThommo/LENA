# HQ Management Console - Universal Build Prompt

Copy everything below this line into Claude Code. Replace every `{{placeholder}}` with your project's values before running.

---

## Task: Build the HQ Management Console

Build a complete management console for this platform. This is the operations hub - it lets the owner, ops team, support agents, and read-only stakeholders see every DB entry, turn data into business intelligence, and handle support.

### Before writing any code:

- Read CLAUDE.md if one exists in the project root
- Read any dev rules or foundation docs referenced there
- Scan the existing codebase to understand the tech stack, folder structure, routing patterns, existing theme/design tokens, and database schema (migrations, models, or ORM files)
- Identify every database table and group them by domain category (users, core entities, money/billing, admin/system, reference data, etc.)

The console MUST inherit the same tech stack, styling conventions, and patterns already used in the main application. Do not introduce new frameworks or libraries unless the project has none.

---

## Architecture: 5 Layers

Generate these as separate files under `src/console/` (isolated from the user-facing app):

### Layer 1: Host-Based Routing (`src/console/consoleRouting.ts`)

- Detect whether the current hostname matches the console subdomain (e.g. `hq.yourapp.com` or `admin.yourapp.com`)
- Export `isConsoleHost()` and `getConsoleRedirectPath()`
- Local dev: support a `?console` query param to simulate the console host
- Block all user-facing routes when on the console host
- If the project has reserved slugs or subdomains, reference them

### Layer 2: Permissions (`src/console/consolePermissions.ts`)

Define a role hierarchy as a const array (index 0 = most powerful):

```typescript
const ROLE_HIERARCHY = ['owner', 'admin', 'support', 'read_only'] as const;
```

Adapt role names to match whatever the project's existing role/permission system uses. If the project has a roles table, SECURITY DEFINER functions, or auth middleware, wire into those directly.

**Permission rules** (adapt labels to your domain):

- **owner** - full access. Sees everything including DB Explorer and Settings.
- **admin** - day-to-day ops. Can modify core entities and data. No system config.
- **support** - user lookup, issue resolution, view financials (no writes on money).
- **read_only** - analytics and aggregate metrics only (stakeholder/investor view, no PII).

**CRITICAL** - use hierarchy INDEX comparison. Never hardcode role strings in permission logic:

```typescript
function roleLevel(role: string): number {
  const idx = (ROLE_HIERARCHY as readonly string[]).indexOf(role);
  return idx === -1 ? ROLE_HIERARCHY.length : idx;
}

function hasMinLevel(userRole: string, requiredLevel: number): boolean {
  return roleLevel(userRole) <= requiredLevel;
}
```

Export a `consoleNav(role)` function that returns a `ConsoleNavVisibility` interface (one boolean per nav item). Every page checks visibility through this interface.

### Layer 3: Theme (`src/console/console-theme.ts` + `src/console/ConsoleThemeProvider.tsx`)

Pull brand colors and fonts from the existing application's theme/config. If the app already uses design tokens, extend them. If not, create a token system using the app's existing brand values.

**Required:**

- Export `darkTheme` and `lightTheme` with an IDENTICAL token shape (`ConsoleThemeTokens` interface)
- Token categories: surfaces (base, raised, sunken), text tiers (primary, secondary, muted), lines/borders, brand accent, semantic colors (success, warning, error, info), money colors (moneyIn green, moneyOut red, moneyPending yellow), spacing scale (4px base), border radius scale, shadows, type scale, font stacks
- Mode persists in localStorage (use a project-specific key)
- `useConsoleTheme()` hook for any child component

### Layer 4: Layout (`src/console/ConsoleLayout.tsx` + `src/console/ImpersonationBanner.tsx`)

3-column CSS grid: `220px 1fr 360px` (nav | main | activity rail)

**Responsive breakpoint ladder:**

- 1440px: rail narrows to 320px
- 1366px: nav collapses to 64px icons only
- 1024px: rail moves below main (2-column)
- 720px: drawer nav, single column

Inject responsive CSS via useEffect with a unique style ID (runs once, no duplicates).

Nav items are typed:

```typescript
interface NavItem {
  label: string;
  path: string;
  group: string;
  key: keyof ConsoleNavVisibility;
  icon: string; // SVG path data
}
```

Filter by `consoleNav(userRole)[item.key]`. Group by `item.group`.

**Include:**

- ImpersonationBanner (sticky top, yellow warning when viewing as another user)
- Theme toggle (dark/light pill)
- User footer (email + role + sign out)
- Activity rail (placeholder for live stats, wire to realtime later)

Wrap the page outlet in `<Suspense>` with a branded loading spinner.

### Layer 5: Routes (`src/console/App.console.tsx`)

All pages lazy-loaded via `React.lazy()`. Nest under ConsoleLayout via the router's outlet pattern.

---

## Pages

Generate one page per major domain area in the application. Every console needs these baseline pages at minimum:

| Page | File | Visible to | Purpose |
|------|------|------------|---------|
| Command Center | CommandCenter.tsx | All | Live KPIs derived from the app's core metrics. Active sessions, revenue today, user growth, pending items. |
| DB Explorer | DBExplorer.tsx | owner | Browse ANY table. See "DB Explorer Specifics" below. |
| Settings | Settings.tsx | owner (view: admin) | Feature flags, console role management, system health checks, audit log viewer. |
| Analytics | Analytics.tsx | All | Growth trends, retention cohorts, revenue trends, engagement metrics, conversion funnels. |

Then add one page per domain category discovered during your codebase scan.

---

## DB Explorer Specifics

The DB Explorer page should:

- List all database tables in a left sidebar, grouped by domain category
- Clicking a table shows rows with pagination (50 rows per page)
- Each column is sortable (click header to toggle asc/desc)
- Basic filter inputs per column (text match for strings, range for numbers/dates)
- Export to CSV button
- "Run SQL" button (owner only) for ad-hoc queries
- If the project uses RLS or row-level security, the explorer should bypass it using a privileged client (service role key, admin connection, etc.)

---

## Key Integration Points

- **Auth:** wire into whatever auth/permission system the project already uses.
- **Audit:** every write action from the console should log to an audit table.
- **Money display:** if money is stored in minor units (cents), convert at the display layer only.
- **Sensitive data:** identify fields that should never leak to user-facing responses (password_hash, reset tokens, etc.).

---

## Command Center KPI Discovery

Do NOT hardcode KPI values. Build KPI cards from a registry array (label, query pattern, format type). Include a time-range selector (today, 7d, 30d, all time).

---

## Rules

- Match the project's existing TypeScript/JavaScript configuration
- Never use em dashes anywhere - use regular hyphen with spaces
- Never delete files
- Surgical edits only (read before edit)
- Desktop-first layout
- All files under `src/console/` to keep them isolated from the user-facing app

---

## Verification

After generating all files, run these checks and report PASS/FAIL for each:

- Type checker passes clean
- All 5 architecture layers are present as separate files
- Every generated page has a route entry
- Permission functions use hierarchy indices
- Theme has both dark and light mode
- Layout responsive breakpoints function at 1366, 1024, and 720px minimum
- Console routes are code-split with lazy loading
- Nav items filtered by permission visibility interface
- Every database table accessible via DB Explorer
- KPI cards driven by a registry (not hardcoded values)

---

# LENA adaptation (this repo)

LENA does **not** use React `src/console/`. HQ is implemented as a static SPA:

| Universal layer | LENA implementation |
|-----------------|---------------------|
| Routing | `frontend/public/hq.html` (path `/hq.html`) |
| Permissions | `backend/app/services/console_permissions.py` |
| Theme | CSS variables in `hq.html` + `localStorage` key `lena.hq.theme` |
| Layout | 3-column grid in `hq.html` (nav / main / activity rail) |
| API | FastAPI routes under `/api/dashboard/platform/console/*` |

**Role mapping (LENA to console hierarchy):**

| LENA `users.role` | Console tier |
|-------------------|--------------|
| `platform_admin` | owner |
| `tenant_admin` | admin |
| `practitioner`, `researcher` | support |
| `public_user` | read_only |

HQ login currently requires `platform_admin`. Additional tiers are wired for future multi-role HQ access.

**Live endpoints:**

- `GET /api/dashboard/platform/console/permissions`
- `GET /api/dashboard/platform/console/kpis`
- `GET /api/dashboard/platform/console/audit-log`
- `GET /api/dashboard/platform/console/db/tables`
- `GET /api/dashboard/platform/console/db/{table}`
- `GET /api/dashboard/platform/console/db/{table}/export`
