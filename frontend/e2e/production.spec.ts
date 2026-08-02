import { test, expect } from '@playwright/test';

const CHAT_INPUT = /ask lena a research question/i;
const PRE_DEPLOY = process.env.E2E_PRE_DEPLOY === '1';

async function healthOk(request: import('@playwright/test').APIRequestContext, baseURL: string) {
  for (const path of ['/api/health', '/api/health/']) {
    const res = await request.get(`${baseURL}${path}`, { maxRedirects: 5 });
    if (res.status() === 200) {
      try {
        const body = await res.json();
        if (body.status === 'healthy') return true;
      } catch {
        /* not JSON */
      }
    }
  }
  return false;
}

test.describe('Public pages', () => {
  test('landing page loads with brand and CTAs', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/LENA/i);
    await expect(page.getByRole('link', { name: /try free/i }).first()).toBeVisible();
    await expect(page.getByText(/PULSE/i).first()).toBeVisible();
    await expect(page.getByText(/Pro/i).first()).toBeVisible();
  });

  test('chat page loads with search input', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.getByPlaceholder(CHAT_INPUT)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /what would you like to research/i })).toBeVisible();
  });

  test('login and register pages load', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByPlaceholder('your@email.com')).toBeVisible();
    await page.goto('/register');
    await expect(page.getByPlaceholder('your@email.com')).toBeVisible();
  });
});

test.describe('API proxy', () => {
  test('same-origin health endpoint returns healthy', async ({ request, baseURL }) => {
    test.skip(PRE_DEPLOY, 'Requires deploy with /api/health route fix');
    expect(await healthOk(request, baseURL!)).toBeTruthy();
  });

  test('same-origin /api/discover/suggestions returns suggestions', async ({ request, baseURL }) => {
    const res = await request.get(`${baseURL}/api/discover/suggestions?persona=general`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.suggestions)).toBeTruthy();
    expect(body.suggestions.length).toBeGreaterThan(0);
  });
});

test.describe('Anonymous search flow', () => {
  test('can run a search in All mode and get results', async ({ page, request, baseURL }) => {
    test.skip(PRE_DEPLOY, 'Requires deploy with All-mode PULSE cap + /api/health fix');
    test.setTimeout(120_000);

    expect(await healthOk(request, baseURL!)).toBeTruthy();

    await page.goto('/chat');
    const input = page.getByPlaceholder(CHAT_INPUT);
    await expect(input).toBeVisible({ timeout: 15_000 });

    await input.fill('What is the evidence for Vitamin D supplementation in immune function?');
    await input.press('Enter');

    const disclaimerAccept = page.getByRole('button', { name: /accept/i });
    if (await disclaimerAccept.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await disclaimerAccept.click();
    }

    await expect(page.getByText(/something didn't work on our side/i)).not.toBeVisible({ timeout: 90_000 });

    const hasResults = page.getByText(/PULSE|Sources \(|confidence/i).first();
    await expect(hasResults).toBeVisible({ timeout: 90_000 });
  });

  test('Pharma mode keeps drug-name results for a biosimilar query', async ({ page, request, baseURL }) => {
    test.skip(PRE_DEPLOY, 'Requires live search backends');
    test.setTimeout(150_000);

    expect(await healthOk(request, baseURL!)).toBeTruthy();

    await page.goto('/chat');
    await expect(page.getByPlaceholder(CHAT_INPUT)).toBeVisible({ timeout: 15_000 });

    await page.getByRole('tab', { name: /^Pharma$/i }).click();
    await expect(page.getByRole('tab', { name: /^Pharma$/i })).toHaveAttribute('aria-selected', 'true');

    const query =
      'Is there trial evidence comparing biosimilar trastuzumab to originator in HER2-positive breast cancer?';
    await page.getByPlaceholder(CHAT_INPUT).fill(query);
    await page.getByPlaceholder(CHAT_INPUT).press('Enter');

    const disclaimerAccept = page.getByRole('button', { name: /accept/i });
    if (await disclaimerAccept.isVisible({ timeout: 8_000 }).catch(() => false)) {
      // After accept, the user bubble for this query must appear only once.
      await disclaimerAccept.click();
      await expect(page.getByText(query)).toHaveCount(1, { timeout: 15_000 });
    }

    await expect(page.getByText(/something didn't work on our side/i)).not.toBeVisible({ timeout: 120_000 });
    await expect(page.getByText(/PULSE/i).first()).toBeVisible({ timeout: 120_000 });
    // Drug token must appear in the answer or sources — not a generic cancer dump.
    await expect(page.getByText(/trastuzumab/i).first()).toBeVisible({ timeout: 30_000 });
  });
});

test.describe('Security', () => {
  test('site is served over HTTPS', async ({ page, baseURL }) => {
    expect(baseURL?.startsWith('https://')).toBeTruthy();
    const res = await page.goto('/');
    expect(res?.url()).toMatch(/^https:\/\//);
  });
});
