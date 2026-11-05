import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('../../../api/places', () => ({
  fetchCollection: vi.fn(() => Promise.resolve({ collection_ids: [], badges: [] })),
}))

import CheckInButton from '../CheckInButton.vue'
import { useLanternsStore } from '../../../stores/lanterns'

const place = { id: 'p1', title: '촉석루', category: 'sight', lat: 35.19, lng: 128.08 }

function mockGeo(impl) {
  const getCurrentPosition = vi.fn(impl)
  Object.defineProperty(globalThis.navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true })
  return getCurrentPosition
}
const ok = (lat, lng, accuracy) => (success) => success({ coords: { latitude: lat, longitude: lng, accuracy } })

async function click(w) {
  await w.find('button').trigger('click')
  await flushPromises()
}

describe('CheckInButton', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  afterEach(() => {
    delete globalThis.navigator.geolocation
  })

  test('lights when near with good accuracy', async () => {
    mockGeo(ok(35.1901, 128.0801, 20))
    const lanterns = useLanternsStore()
    const w = mount(CheckInButton, { props: { place } })
    expect(w.text()).toContain('도착했어요')
    await click(w)
    expect(lanterns.isLit('p1')).toBe(true)
    expect(lanterns.items.p1.litMethod).toBe('gps')
    expect(w.emitted('lit')).toBeTruthy()
  })

  test('low accuracy shows message and does not light', async () => {
    mockGeo(ok(35.19, 128.08, 2000))
    const lanterns = useLanternsStore()
    const w = mount(CheckInButton, { props: { place } })
    await click(w)
    expect(w.text()).toContain('위치 정확도가 낮아요')
    expect(lanterns.isLit('p1')).toBe(false)
  })

  test('permission denied message', async () => {
    mockGeo((_s, error) => error({ code: 1 }))
    const lanterns = useLanternsStore()
    const w = mount(CheckInButton, { props: { place } })
    await click(w)
    expect(w.text()).toContain('위치 권한이 필요해요')
    expect(lanterns.isLit('p1')).toBe(false)
  })

  test('too far shows distance', async () => {
    mockGeo(ok(35.21, 128.08, 10))
    const w = mount(CheckInButton, { props: { place } })
    await click(w)
    expect(w.text()).toMatch(/아직 \d+(\.\d)?(km|m) 떨어져 있어요/)
    expect(useLanternsStore().isLit('p1')).toBe(false)
  })

  test('demo mode without a dragged pin checks against the default pin (촉석루) and never reads GPS', async () => {
    const spy = mockGeo(ok(0, 0, 1))
    const lanterns = useLanternsStore()
    lanterns.setDemo({ enabled: true })
    const far = { id: 'p-far', title: '먼 곳', category: 'sight', lat: 35.25, lng: 128.2 }
    const wFar = mount(CheckInButton, { props: { place: far } })
    await click(wFar)
    expect(spy).not.toHaveBeenCalled()
    expect(wFar.text()).toContain('떨어져 있어요')
    expect(lanterns.isLit('p-far')).toBe(false)

    const w = mount(CheckInButton, { props: { place: { ...place, lat: 35.1898, lng: 128.0820 } } })
    expect(w.text()).toContain('도착 시뮬레이션')
    expect(w.text()).toContain('시연 모드')
    await click(w)
    expect(spy).not.toHaveBeenCalled()
    expect(lanterns.isLit('p1')).toBe(true)
    expect(lanterns.items.p1.litMethod).toBe('demo')
  })

  test('demo mode with virtual pin 2km away is too far', async () => {
    const spy = mockGeo(ok(0, 0, 1))
    const lanterns = useLanternsStore()
    // ~2.0km north of the place
    lanterns.setDemo({ enabled: true, pos: { lat: 35.19 + 2000 / 111195, lng: 128.08 } })
    const w = mount(CheckInButton, { props: { place } })
    await click(w)
    expect(spy).not.toHaveBeenCalled()
    expect(w.text()).toContain('아직 2.0km 떨어져 있어요')
    expect(lanterns.isLit('p1')).toBe(false)
  })

  test('already lit shows lit state', () => {
    const lanterns = useLanternsStore()
    lanterns.light('p1', 'demo', place)
    const w = mount(CheckInButton, { props: { place } })
    expect(w.text()).toContain('밝혔어요')
    expect(w.find('button').exists()).toBe(false)
  })
})
