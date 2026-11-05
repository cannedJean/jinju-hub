import { test, expect, isMobile, screenshotPath, expectNoOverlap } from './support'

const chatBubble = (page) => page.getByRole('button', { name: '챗봇 열기' })
const tabBar = (page) => page.getByRole('navigation', { name: '하단 메뉴' })

test('explore layout per viewport', async ({ page }, testInfo) => {
  await page.goto('/explore')
  const panel = page.getByRole('complementary', { name: '장소 목록' })
  await expect(page.locator('article[data-place-id]').first()).toBeAttached()

  if (isMobile(testInfo)) {
    await expect(tabBar(page)).toBeVisible()
    await expect(page.getByRole('navigation', { name: '주 메뉴' })).toBeHidden()
    await expect(panel).toHaveCount(0)
    await expect(page.getByTestId('sheet')).toBeVisible()
    // The chat bubble must leave the tab bar (incl. 더보기) uncovered and clickable.
    const more = tabBar(page).getByRole('button', { name: '더보기' })
    await expectNoOverlap(chatBubble(page), tabBar(page), 'chat bubble vs tab bar')
    await expectNoOverlap(chatBubble(page), page.getByTestId('sheet'), 'chat bubble vs collapsed sheet')
    await more.click()
    await expect(page.getByRole('menu', { name: '더보기' })).toBeVisible()
    await page.getByTestId('more-backdrop').click()
  } else {
    await expect(page.getByRole('navigation', { name: '주 메뉴' })).toBeVisible()
    await expect(tabBar(page)).toHaveCount(0)
    await expect(panel).toBeVisible()
    const { width } = await panel.boundingBox()
    if (testInfo.project.name === 'desktop') expect(width).toBeGreaterThanOrEqual(400)
    else expect(width).toBeGreaterThanOrEqual(320)
  }

  await page.screenshot({ path: screenshotPath(testInfo, 'explore') })
})

test('demo banner stacks above the sticky header', async ({ page }, testInfo) => {
  await page.goto('/festivals?demo=1')
  const banner = page.getByRole('status').filter({ hasText: '시연 모드' })
  const header = page.getByRole('banner')
  await expect(banner).toBeVisible()
  await expect(page.getByTestId('festival-card').first()).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 600))
  await expect.poll(async () => (await header.boundingBox()).y).toBe(32)
  const b = await banner.boundingBox()
  expect(b.y).toBe(0)
  expect(b.height).toBe(32)
  await page.screenshot({ path: screenshotPath(testInfo, 'demo-banner-header') })
})

test('undo snackbar clears the chat bubble and the tab bar', async ({ page }, testInfo) => {
  await page.goto('/places/jh-14496674c7')
  await page.getByRole('button', { name: '◇ 유등 띄우기(담기)' }).click()
  await page.getByTestId('lantern-progress').click()
  await expect(page).toHaveURL(/\/lanterns/)
  await page.getByRole('button', { name: '빼기 진주성' }).click()
  const snackbar = page.getByRole('status').filter({ hasText: '빼기 완료' })
  await expect(snackbar).toBeVisible()
  await page.screenshot({ path: screenshotPath(testInfo, 'undo-snackbar') })
  await expectNoOverlap(snackbar, chatBubble(page), 'undo snackbar vs chat bubble')
  if (isMobile(testInfo)) await expectNoOverlap(snackbar, tabBar(page), 'undo snackbar vs tab bar')
  await snackbar.getByRole('button', { name: '실행 취소' }).click()
  await expect(page.locator('[data-place-id="jh-14496674c7"]').first()).toBeVisible()
})
