import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'

// READ-ONLY smoke against the deployed site. Runs only through `LIVE_URL=... npm run e2e:live`
// (playwright.config.js ignores this file otherwise). It deliberately does not use ./support:
// map tiles and place images must load for real. It only navigates and reads: no lantern saves,
// no board posts, no chat messages.
const LIVE_URL = process.env.LIVE_URL
const API_HEALTH = process.env.LIVE_API_URL ?? 'https://jinjuhub-api.onrender.com/api/health'
const SHOT_DIR = process.env.LIVE_SCREENSHOTS // set to a directory to also capture README screenshots

test.skip(!LIVE_URL, 'set LIVE_URL to run the live smoke')
test.describe.configure({ mode: 'serial' })
test.setTimeout(120_000)

const SLOW = { timeout: 60_000 }

test.beforeAll(async ({ request }) => {
  // Render free tier sleeps after 15 min idle; the cold start takes ~50 s.
  await expect
    .poll(async () => (await request.get(API_HEALTH, { timeout: 30_000 }).catch(() => null))?.status(), {
      timeout: 120_000,
      intervals: [2_000, 5_000],
    })
    .toBe(200)
})

const shot = async (page, name) => {
  if (!SHOT_DIR) return
  mkdirSync(SHOT_DIR, { recursive: true })
  await page.waitForTimeout(1_500) // let map tiles settle
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png` })
}

test('home shows the hero', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1, name: '진주, 남강에 유등을 띄우다' })).toBeVisible(SLOW)
})

test('explore shows the map and place cards', async ({ page }, testInfo) => {
  await page.goto('/explore')
  await expect(page.locator('.leaflet-container')).toBeVisible(SLOW)
  if (testInfo.project.name === 'mobile') {
    const sheet = page.getByTestId('sheet')
    if ((await sheet.getAttribute('data-snap')) === 'collapsed') await page.getByTestId('sheet-handle').click()
  }
  await expect(page.locator('article[data-place-id]').first()).toBeVisible(SLOW)
  await shot(page, `explore-${testInfo.project.name}`)
})

test('place detail renders a title', async ({ page }, testInfo) => {
  await page.goto('/explore')
  const first = page.locator('article[data-place-id]').first()
  await expect(first).toBeAttached(SLOW)
  const id = await first.getAttribute('data-place-id')
  await page.goto(`/places/${id}`)
  await expect(page.getByRole('heading', { level: 1 }).first()).not.toBeEmpty(SLOW)
  await expect(page.getByRole('heading', { level: 1, name: '더 이상 제공되지 않는 장소예요' })).toHaveCount(0)
  await shot(page, `detail-${testInfo.project.name}`)
})

test('festivals page renders', async ({ page }) => {
  await page.goto('/festivals')
  await expect(page.getByRole('heading', { level: 1, name: '축제·행사' })).toBeVisible(SLOW)
  await expect(page.getByTestId('festival-card').first()).toBeVisible(SLOW)
})

test('data sources page shows the report numbers', async ({ page }) => {
  await page.goto('/about/data')
  await expect(page.getByRole('heading', { level: 1, name: '데이터 출처' })).toBeVisible(SLOW)
  await expect(page.getByTestId('report-card')).toHaveCount(4, SLOW)
  await expect(page.getByTestId('source-row').first()).toBeVisible()
})

test('board list shows at least one post', async ({ page }) => {
  await page.goto('/boards')
  await expect(page.getByRole('heading', { level: 1, name: '커뮤니티 게시판' })).toBeVisible(SLOW)
  const posts = page.locator('main button').filter({ has: page.locator('.cat-badge') })
  await expect(posts.first()).toBeVisible(SLOW)
})
