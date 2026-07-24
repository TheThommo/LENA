import { test, expect } from '@playwright/test';
import {
  applySessionRename,
  mergeProjectSessions,
  type RecentSessionRecord,
} from '../src/lib/sessionTime';

/**
 * Project sidebar smoke — collapse, rename, restore-without-research, no dupes.
 * Seeds auth + local history and mocks project APIs so we never hit production.
 */

const USER_ID = 'smoke-user-1';
const PROJECT_ID = 'proj-energy';
const SESSION_ID = '1700000000001';
const QUERY = 'Energy levels are low in the morning';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    sub: USER_ID,
    exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 365,
  })).toString('base64url');
  return `${header}.${payload}.smoke`;
}

function seedSession(): RecentSessionRecord {
  return {
    id: SESSION_ID,
    firstQuery: QUERY,
    queries: [QUERY],
    projectId: PROJECT_ID,
    createdAt: new Date().toISOString(),
    lastActivityAt: new Date().toISOString(),
  };
}

test.describe('Project sidebar UX', () => {
  test('unit: merge + rename do not duplicate', () => {
    const local = [seedSession()];
    const remote = [{
      ...seedSession(),
      id: 'uuid-from-api',
    }];
    const merged = mergeProjectSessions(local, remote);
    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe(SESSION_ID);

    const renamed = applySessionRename(
      [...local, remote[0]],
      'uuid-from-api',
      'Morning energy',
      remote[0],
    );
    expect(renamed).toHaveLength(1);
    expect(renamed[0].title).toBe('Morning energy');
  });

  test('browser: collapse, rename, open past chat without new search', async ({ page }) => {
    const token = fakeJwt();
    const user = {
      id: USER_ID,
      email: 'smoke@lena.test',
      name: 'Smoke',
      role: 'user',
      tenant_id: 'tenant-1',
      created_at: new Date().toISOString(),
    };
    const project = {
      id: PROJECT_ID,
      name: 'Energy',
      description: null,
      color: null,
      emoji: '⚡',
      archived_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      search_count: 2,
    };
    const session = seedSession();
    // Deliberate duplicate remote id for same query — UI must show one row.
    const remoteDuplicate = { ...session, id: 'uuid-dup-search' };

    let searchPosts = 0;

    await page.route('**/auth/me', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
    });
    await page.route('**/projects/limits', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ plan: 'pro', max_active: null, active_count: 1, can_create: true }),
      });
    });
    await page.route('**/projects/*/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_id: PROJECT_ID,
          searches: [
            {
              id: 'uuid-dup-search',
              query: QUERY,
              created_at: session.createdAt,
              session_id: null,
              project_id: PROJECT_ID,
            },
            {
              id: 'uuid-dup-search-2',
              query: QUERY,
              created_at: session.createdAt,
              session_id: SESSION_ID,
              project_id: PROJECT_ID,
            },
          ],
        }),
      });
    });
    await page.route('**/projects**', async (route) => {
      const url = route.request().url();
      if (url.includes('/searches') || url.includes('/limits')) {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([project]),
      });
    });
    await page.route('**/search**', async (route) => {
      if (route.request().method() === 'POST') {
        searchPosts += 1;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'search should not run' }),
      });
    });

    await page.addInitScript(({ token, user, session, remoteDuplicate, projectId, userId }) => {
      localStorage.setItem('lena_token', token);
      localStorage.setItem('lena_user', JSON.stringify(user));
      localStorage.setItem(`lena_recent_sessions_${userId}`, JSON.stringify([session, remoteDuplicate]));
      localStorage.setItem(`lena_active_project_id_${userId}`, projectId);
      localStorage.setItem(`lena_session_threads_${userId}`, JSON.stringify({
        [session.id]: [
          {
            id: 'm1',
            type: 'user',
            content: session.firstQuery,
            timestamp: new Date().toISOString(),
          },
          {
            id: 'm2',
            type: 'assistant',
            content: 'Cached PULSE summary — should restore without a new search.',
            timestamp: new Date().toISOString(),
            response: {
              llm_summary: 'Cached PULSE summary — should restore without a new search.',
              search_id: 'search-cached-1',
              query: session.firstQuery,
              total_results: 1,
              sources_queried: ['pubmed'],
              sources_failed: {},
              pulse_report: {
                status: 'validated',
                confidence_ratio: 0.8,
                consensus_keywords: [],
                consensus_summary: 'Cached summary',
                validated_results: [],
                edge_cases: [],
                source_agreements: [],
                total_cross_validations: 0,
              },
              validated_results: [],
              edge_cases: [],
            },
          },
        ],
      }));
    }, { token, user, session, remoteDuplicate, projectId: PROJECT_ID, userId: USER_ID });

    await page.goto('/chat');
    await expect(page.getByText('Energy').first()).toBeVisible({ timeout: 20_000 });

    // Deduped: only one nested chat label for the query (not two).
    const chatButtons = page.locator(`[data-testid^="open-session-"]`);
    await expect(chatButtons).toHaveCount(1);

    // Collapse via project title
    await page.getByTestId(`project-title-${PROJECT_ID}`).click();
    await expect(page.getByTestId(`project-chats-${PROJECT_ID}`)).toHaveCount(0);
    await expect(page.getByTestId(`project-collapse-${PROJECT_ID}`)).toHaveAttribute('aria-expanded', 'false');

    // Expand again
    await page.getByTestId(`project-title-${PROJECT_ID}`).click();
    await expect(page.getByTestId(`project-chats-${PROJECT_ID}`)).toBeVisible();

    // Rename
    const openBtn = page.locator(`[data-testid^="open-session-"]`).first();
    const sessionTestId = await openBtn.getAttribute('data-testid');
    const sid = sessionTestId!.replace('open-session-', '');
    await page.getByTestId(`rename-session-${sid}`).click();
    await page.getByTestId(`rename-input-${sid}`).fill('Morning energy notes');
    await page.getByTestId(`rename-input-${sid}`).press('Enter');
    await expect(page.getByText('Morning energy notes')).toBeVisible();
    await expect(chatButtons).toHaveCount(1);

    // Open past chat — must restore cache, no POST /search
    searchPosts = 0;
    await page.getByTestId(`open-session-${sid}`).click();
    await expect(page.getByText('Cached PULSE summary — should restore without a new search.')).toBeVisible({
      timeout: 10_000,
    });
    await expect.poll(() => searchPosts).toBe(0);
  });
});
