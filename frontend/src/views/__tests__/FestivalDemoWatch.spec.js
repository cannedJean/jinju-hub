import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { nextTick } from 'vue'

vi.mock('../../api/places', () => ({
  fetchFestivals: vi.fn(),
  fetchCollection: vi.fn(() => Promise.resolve({ collection_ids: [], badges: [] })),
  fetchMeta: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../../api/weather', () => ({ fetchWeather: vi.fn(() => Promise.resolve({})) }))

import HomeView from '../HomeView.vue'
import FestivalsView from '../FestivalsView.vue'
import { fetchFestivals } from '../../api/places'
import { useLanternsStore } from '../../stores/lanterns'

const Stub = { template: '<div />' }
function plugins() {
  return [createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: Stub }, { path: '/:p(.*)*', component: Stub }] })]
}

beforeEach(() => {
  vi.clearAllMocks()
  fetchFestivals.mockResolvedValue({ items: [], today: '2026-11-04' })
})

describe.each([['HomeView', HomeView], ['FestivalsView', FestivalsView]])('%s demo watcher', (_n, View) => {
  test('pos change does not reload; today/enabled change reloads once each', async () => {
    const w = mount(View, { global: { plugins: plugins() } })
    await flushPromises()
    const lanterns = useLanternsStore()
    expect(fetchFestivals).toHaveBeenCalledTimes(1)

    lanterns.setDemo({ enabled: false, today: '', pos: { lat: 35.1, lng: 128.1 } })
    await flushPromises()
    expect(fetchFestivals).toHaveBeenCalledTimes(1)

    lanterns.setDemo({ enabled: true, today: '2026-10-05', pos: { lat: 35.1, lng: 128.1 } })
    await flushPromises()
    expect(fetchFestivals).toHaveBeenCalledTimes(2)

    lanterns.setDemo({ enabled: true, today: '2026-10-05', pos: { lat: 35.2, lng: 128.2 } })
    await flushPromises()
    expect(fetchFestivals).toHaveBeenCalledTimes(2)
    w.unmount()
  })
})

describe('HomeView banner', () => {
  test('no empty parentheses when date range is empty', async () => {
    fetchFestivals.mockResolvedValue({
      items: [{ id: 'a', title: '유등제', status: 'ongoing', start_date: '', end_date: '' }],
      today: '2026-11-04',
    })
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    await nextTick()
    expect(w.text()).toContain('지금 진행 중: 유등제')
    expect(w.text()).not.toContain('()')
    expect(w.text()).not.toMatch(/유등제\s*\(\s*\)/)
  })
  test('shows range in parentheses when present', async () => {
    fetchFestivals.mockResolvedValue({
      items: [{ id: 'a', title: '유등제', status: 'ongoing', start_date: '2026-10-01', end_date: '2026-10-10' }],
      today: '2026-10-05',
    })
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    expect(w.text()).toContain('유등제 (10.1 ~ 10.10)')
  })
})
