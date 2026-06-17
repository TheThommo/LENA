# LENA HQ Console — Build Prompt

> **Note:** Drop your full build specification here. The file path on your machine was:
> `/Users/Thommo_1/Projects/LENA/HQ_Console_Build_Prompt.md`
>
> Commit this file to the repo so Cloud Agents and collaborators can align the HQ UI to your template.

## Reference architecture (in repo)

- `docs/buddees-reference/Buddees_Console_Architecture_Brief.md` — HQ layout, nav groups, activity rail, drill-down patterns
- `frontend/public/hq.html` — LENA HQ implementation (static SPA, same pattern as `admin.html`)

## LENA HQ scope (POC)

| Section | Status | API |
|---------|--------|-----|
| Command Center | Live | `/dashboard/platform/overview`, `/revenue`, `/tenants` |
| Revenue | Live | `/dashboard/platform/revenue` |
| Tenants | Live | `/dashboard/platform/tenants` |
| Subscriptions | Live | `/dashboard/platform/subscriptions` |
| Users | Live | `/dashboard/platform/user-directory` |
| LLM Costs | Live | `/dashboard/platform/costs` |
| System Health | Live | `/api/health` + overview stats |
| Product Intelligence | Link | `/admin.html` |
| Invoices, Growth, Audit, Goals | Planned | Not yet built |

## Paste your template below

<!-- USER: paste HQ_Console_Build_Prompt.md content below this line -->
