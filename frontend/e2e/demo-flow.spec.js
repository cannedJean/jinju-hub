import { test, expect, isMobile, navigate, openDemoSettings, openSheet, screenshotPath, expectNoOverlap } from './support'

// 진주성 in the fixture places db (tests/fixtures/places_fixture.db).
const JINJUSEONG = { id: 'jh-14496674c7', latitude: 35.18952066914974, longitude: 128.07996337934236 }

test('demo script: explore -> lodging radius -> save -> demo check-in -> badge -> festival date', async ({
  page,
  context,
}, testInfo) => {
  const mobile = isMobile(testInfo)
  // No geolocation and no seeded state: demo mode's virtual pin (default 촉석루) is the user's position.

  // 1. Demo mode from the shared link.
  await page.goto('/?demo=1')
  const banner = page.getByRole('status').filter({ hasText: '시연 모드' })
  await expect(banner).toBeVisible()

  // 2. Hero CTA -> explore.
  await page.getByRole('link', { name: '지도에서 탐색' }).click()
  await expect(page).toHaveURL(/\/explore/)
  await expect(page.getByText(/^장소 \d+곳$/).first()).toBeAttached()

  // 3. Category chip 맛집.
  const food = page.getByRole('group', { name: '카테고리 필터' }).getByRole('button', { name: /맛집/ })
  await food.click()
  await expect(food).toHaveAttribute('aria-pressed', 'true')
  await expect(page).toHaveURL(/cat=food/)

  // 4. Drag the map, then "이 지역 재검색" -> the list is limited to the visible area.
  const map = page.locator('.leaflet-container')
  const box = await map.boundingBox()
  const x = box.x + box.width / 2
  const y = box.y + box.height * 0.45
  await page.mouse.move(x, y)
  await page.mouse.down()
  await page.mouse.move(x - 140, y + 60, { steps: 10 })
  await page.mouse.up()
  const research = page.getByRole('button', { name: '이 지역 재검색' })
  await expect(research).toBeVisible()
  await research.click()
  await expect(research).toBeHidden()
  await expect(page).toHaveURL(/bbox=/)
  await expect(page.getByText(/지도 영역 안 \d+곳/).first()).toBeAttached()

  // 5. 내 숙소: current location (demo mode: the virtual pin), radius 5km, nearest first.
  if (mobile) await openSheet(page)
  await page.getByRole('button', { name: '현재 위치' }).click()
  // The default 1km may hold no food place around 촉석루 in the fixture db: widen to 5km (as a presenter would).
  const radiusGroup = page.getByRole('group', { name: '숙소 반경' })
  const radius5k = radiusGroup.getByRole('button', { name: '5km', exact: true })
  await expect(radius5k).toBeVisible()
  await radius5k.click()
  await expect(radius5k).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText(/숙소 5km 안 \d+곳/).first()).toBeAttached()

  // 6. First card shows its distance from the lodging.
  const firstCard = page.locator('article[data-place-id]').first()
  await expect(firstCard).toContainText(/\d(\.\d)?(m|km)/)

  // 7. Detail -> 담기 -> 도착 시뮬레이션.
  const link = firstCard.getByRole('link').first()
  const title = (await link.innerText()).trim()
  await link.click()
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  await page.getByRole('button', { name: '◇ 유등 띄우기(담기)' }).click()
  await expect(page.getByRole('button', { name: '◇ 담음 · 빼기' })).toBeVisible()
  await page.getByRole('button', { name: '도착 시뮬레이션' }).click()
  // The virtual pin moved to the place (no distance check in demo mode).
  await expect
    .poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('jinjuhub.lanterns.v1')).demo.pos))
    .toMatchObject({ lat: expect.any(Number), lng: expect.any(Number) })
  const pos = await page.evaluate(() => JSON.parse(localStorage.getItem('jinjuhub.lanterns.v1')).demo.pos)
  expect(Math.abs(pos.lat - 35.1897) + Math.abs(pos.lng - 128.0819)).toBeGreaterThan(0.0005)

  // 8. First-light toast (announced + shown), lit state, header progress.
  await expect(page.getByRole('status').filter({ hasText: '첫 유등을 밝혔어요!' })).toBeAttached()
  const toast = page.locator('.toast').filter({ hasText: '첫 유등을 밝혔어요!' })
  await expect(toast).toBeVisible()
  await page.screenshot({ path: screenshotPath(testInfo, 'first-light-toast') })
  await expectNoOverlap(toast, page.getByRole('button', { name: '챗봇 열기' }), 'toast vs chat bubble')
  if (mobile) await expectNoOverlap(toast, page.getByRole('navigation', { name: '하단 메뉴' }), 'toast vs tab bar')
  await expect(page.getByText('◆ 이곳의 유등을 밝혔어요')).toBeVisible()
  await expect(page.getByTestId('lantern-progress')).toContainText('◆')

  // 9. 내 유등: the 첫 등불 badge is earned.
  await page.getByTestId('lantern-progress').click()
  await expect(page).toHaveURL(/\/lanterns/)
  const firstLight = page.getByRole('list', { name: '배지 진열장' }).getByRole('listitem').filter({ hasText: '첫 등불' })
  await expect(firstLight).toHaveAttribute('data-earned', 'true')
  await expect(firstLight).toContainText('획득')

  // 10. Demo reference date preset: 유등축제 기간.
  const dialog = await openDemoSettings(page, testInfo)
  await dialog.getByRole('button', { name: '유등축제 기간(2026-10-10)' }).click()
  await expect(banner).toContainText('기준일 2026-10-10')
  await dialog.getByRole('button', { name: '시연 설정 닫기' }).click()
  await expect(dialog).toBeHidden()

  // 11. Festivals: 진주남강유등축제 is ongoing on the demo date.
  await navigate(page, testInfo, '축제')
  await expect(page).toHaveURL(/\/festivals/)
  const yudeung = page.getByTestId('festival-card').filter({ hasText: '진주남강유등축제' })
  await expect(yudeung.getByTestId('status-chip')).toHaveText('진행 중')
})

test('real GPS check-in lights 진주성 only when close enough', async ({ page, context }) => {
  await page.goto(`/places/${JINJUSEONG.id}`)
  await expect(page.getByRole('heading', { level: 1, name: '진주성' })).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: '시연 모드' })).toHaveCount(0)

  // ~530m away (the plan's sample point): rejected with the distance.
  await context.setGeolocation({ latitude: 35.1925, longitude: 128.0845, accuracy: 20 })
  const arrive = page.getByRole('button', { name: '도착했어요' })
  await arrive.click()
  await expect(page.getByText(/아직 .* 떨어져 있어요/)).toBeVisible()

  // At 진주성 with good accuracy: lit.
  await context.setGeolocation({ latitude: JINJUSEONG.latitude, longitude: JINJUSEONG.longitude, accuracy: 20 })
  await arrive.click()
  await expect(page.getByText('◆ 이곳의 유등을 밝혔어요')).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: '첫 유등을 밝혔어요!' })).toBeAttached()
  await expect(page.getByRole('button', { name: '◆ 밝힘' })).toBeDisabled()
})
