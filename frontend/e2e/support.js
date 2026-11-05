import { test as base, expect } from '@playwright/test'

// Shared e2e helpers. Every test runs offline: anything outside the local dev servers
// (map tiles, remote images) is aborted so the run is deterministic and never touches the network.
const LOCAL = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//

export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route(
      (url) => !LOCAL.test(url.href) && !url.href.startsWith('data:') && !url.href.startsWith('blob:'),
      (route) => route.abort(),
    )
    await use(context)
  },
})

export { expect }

export const isMobile = (testInfo) => testInfo.project.name === 'mobile'

// Screenshots for the visual layout review land in test-results/screens/.
export function screenshotPath(testInfo, name) {
  return `test-results/screens/${testInfo.project.name}-${name}.png`
}

// Mobile explore keeps the list in a bottom sheet: open it to the half snap before using it.
export async function openSheet(page) {
  const sheet = page.getByTestId('sheet')
  if ((await sheet.getAttribute('data-snap')) === 'collapsed') await page.getByTestId('sheet-handle').click()
  await expect(sheet).not.toHaveAttribute('data-snap', 'collapsed')
}

// Demo settings: footer link on wide screens, 더보기 menu in the mobile tab bar.
export async function openDemoSettings(page, testInfo) {
  if (isMobile(testInfo)) {
    await page.getByRole('navigation', { name: '하단 메뉴' }).getByRole('button', { name: '더보기' }).click()
    await page.getByRole('menuitem', { name: '시연 설정' }).click()
  } else {
    await page.getByRole('contentinfo').getByRole('button', { name: '시연 설정' }).click()
  }
  const dialog = page.getByRole('dialog', { name: '시연 설정' })
  await expect(dialog).toBeVisible()
  return dialog
}

// Top-level navigation: header menu on wide screens, bottom tab bar on mobile.
export async function navigate(page, testInfo, label) {
  const nav = isMobile(testInfo)
    ? page.getByRole('navigation', { name: '하단 메뉴' })
    : page.getByRole('navigation', { name: '주 메뉴' })
  await nav.getByRole('link', { name: label }).click()
}

// Fails when two visible elements' boxes intersect (layout collisions: toasts, chat bubble, tab bar).
export async function expectNoOverlap(a, b, label) {
  const [ra, rb] = [await a.boundingBox(), await b.boundingBox()]
  expect(ra, `${label}: first element not visible`).not.toBeNull()
  expect(rb, `${label}: second element not visible`).not.toBeNull()
  const overlaps =
    ra.x < rb.x + rb.width && rb.x < ra.x + ra.width && ra.y < rb.y + rb.height && rb.y < ra.y + ra.height
  expect(overlaps, `${label}: ${JSON.stringify(ra)} overlaps ${JSON.stringify(rb)}`).toBe(false)
}
