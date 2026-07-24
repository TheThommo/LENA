import { test, expect } from '@playwright/test';
import {
  applySessionRename,
  mergeProjectSessions,
  type RecentSessionRecord,
} from '../src/lib/sessionTime';

/**
 * Project sidebar smoke — collapse, rename, restore-without-research,
 * distinct searches with the same query text stay distinct.
 * Seeds auth + local history and mocks project APIs so we never hit production.
 */

const USER_ID = 'smoke-user-1';
const PROJECT_ID = 'proj-energy';
const SESSION_A = '1700000000001';
const SESSION_B = '1700000000002';
const SEARCH_A = 'search-aaa-111';
const SEARCH_B = 'search-bbb-222';
const QUERY = 'Energy levels are low in the morning';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    sub: USER_ID,
    exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 365,
  })).toString('base64url');
  return `${header}.${payload}.smoke`;
}

function seedSession(id: string, searchId: string, title?: string): RecentSessionRecord {
  return {
    id,
    searchId,
    firstQuery: QUERY,
    title,
    queries: [QUERY],
    projectId: PROJECT_ID,
    createdAt: new Date().toISOString(),
    lastActivityAt: new Date().toISOString(),
  };
}

test.describe('Project sidebar UX', () => {
  test('unit: same query stays two rows; searchId aliases local+remote', () => {
    const localA = seedSession(SESSION_A, SEARCH_A, 'Test 1');
    const localB = seedSession(SESSION_B, SEARCH_B);
    const remoteA = {
      id: SEARCH_A,
      searchId: SEARCH_A,
      firstQuery: QUERY,
      queries: [QUERY],
      projectId: PROJECT_ID,
      createdAt: localA.createdAt,
      lastActivityAt: localA.lastActivityAt,
    };
    const remoteB = {
      id: SEARCH_B,
      searchId: SEARCH_B,
      firstQuery: QUERY,
      queries: [QUERY],
      projectId: PROJECT_ID,
      createdAt: localB.createdAt,
      lastActivityAt: localB.lastActivityAt,
    };

    const merged = mergeProjectSessions([localA, localB], [remoteA, remoteB]);
    expect(merged).toHaveLength(2);
    expect(merged.some(s => s.title === 'Test 1')).toBe(true);
    expect(merged.every(s => (s.firstQuery || '').toLowerCase() === QUERY.toLowerCase())).toBe(true);

    // True alias: local Date.now id later stamped with searchId matches remote search id
    const localOnly: RecentSessionRecord = {
      id: SESSION_A,
      firstQuery: QUERY,
      queries: [QUERY],
      projectId: PROJECT_ID,
      searchId: SEARCH_A,
      createdAt: new Date().toISOString(),
      lastActivityAt: new Date().toISOString(),
    };
    const aliased = mergeProjectSessions([localOnly], [remoteA]);
    expect(aliased).toHaveLength(1);

    const renamed = applySessionRename(
      [localA, localB],
      SESSION_A,
      'Morning energy',
      localA,
    );
    expect(renamed).toHaveLength(2);
    expect(renamed.find(s => s.id === SESSION_A)?.title).toBe('Morning energy');
    expect(renamed.find(s => s.id === SESSION_B)?.title).toBeUndefined();
  });

  test('browser: two same-query searches both listed; rename; open without re-search', async ({ page }) => {
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
    const sessionA = seedSession(SESSION_A, SEARCH_A, 'Test 1');
    const sessionB = seedSession(SESSION_B, SEARCH_B);

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
              id: SEARCH_B,
              query: QUERY,
              created_at: sessionB.createdAt,
              session_id: null,
              project_id: PROJECT_ID,
            },
            {
              id: SEARCH_A,
              query: QUERY,
              created_at: sessionA.createdAt,
              session_id: SESSION_A,
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

    await page.addInitScript(({ token, user, sessionA, sessionB, projectId, userId }) => {
      localStorage.setItem('lena_token', token);
      localStorage.setItem('lena_user', JSON.stringify(user));
      localStorage.setItem(`lena_recent_sessions_${userId}`, JSON.stringify([sessionA, sessionB]));
      localStorage.setItem(`lena_active_project_id_${userId}`, projectId);
      localStorage.setItem(`lena_session_threads_${userId}`, JSON.stringify({
        [sessionA.id]: [
          {
            id: 'm1',
            type: 'user',
            content: sessionA.firstQuery,
            timestamp: new Date().toISOString(),
          },
          {
            id: 'm2',
            type: 'assistant',
            content: 'Cached PULSE summary — should restore without a new search.',
            timestamp: new Date().toISOString(),
            response: {
              llm_summary: 'Cached PULSE summary — should restore without a new search.',
              search_id: sessionA.searchId,
              query: sessionA.firstQuery,
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
    }, { token, user, sessionA, sessionB, projectId: PROJECT_ID, userId: USER_ID });

    await page.goto('/chat');
    await expect(page.getByText('Energy').first()).toBeVisible({ timeout: 20_000 });

    // Two distinct searches with the same query must both appear under the project.
    const chatButtons = page.locator(`[data-testid^="open-session-"]`);
    await expect(chatButtons).toHaveCount(2);
    await expect(page.getByText('Test 1')).toBeVisible();

    // Collapse via project title
    await page.getByTestId(`project-title-${PROJECT_ID}`).click();
    await expect(page.getByTestId(`project-chats-${PROJECT_ID}`)).toHaveCount(0);
    await expect(page.getByTestId(`project-collapse-${PROJECT_ID}`)).toHaveAttribute('aria-expanded', 'false');

    // Expand again
    await page.getByTestId(`project-title-${PROJECT_ID}`).click();
    await expect(page.getByTestId(`project-chats-${PROJECT_ID}`)).toBeVisible();
    await expect(chatButtons).toHaveCount(2);

    // Rename one row only
    await page.getByTestId(`rename-session-${SESSION_A}`).click();
    await page.getByTestId(`rename-input-${SESSION_A}`).fill('Morning energy notes');
    await page.getByTestId(`rename-input-${SESSION_A}`).press('Enter');
    await expect(page.getByText('Morning energy notes')).toBeVisible();
    await expect(chatButtons).toHaveCount(2);

    // Open past chat — must restore cache, no POST /search
    searchPosts = 0;
    await page.getByTestId(`open-session-${SESSION_A}`).click();
    await expect(page.getByText('Cached PULSE summary — should restore without a new search.')).toBeVisible({
      timeout: 10_000,
    });
    await expect.poll(() => searchPosts).toBe(0);
  });
});
