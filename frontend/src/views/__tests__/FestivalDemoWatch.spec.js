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

describe('HomeView cold-start failure', () => {
  test('while the first request is pending a neutral loading banner shows, not the fallback', async () => {
    let resolve
    fetchFestivals.mockReturnValueOnce(new Promise((r) => (resolve = r)))
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    expect(w.find('[data-test="festival-loading"]').text()).toContain('축제 정보를 불러오는 중')
    expect(w.text()).not.toContain('유등축제는 매년 10월')
    resolve({ items: [], today: '2026-11-04' })
    await flushPromises()
    expect(w.find('[data-test="festival-loading"]').exists()).toBe(false)
    expect(w.text()).toContain('유등축제는 매년 10월')
  })

  test('shows an explicit retry state instead of the fallback banner, and retries', async () => {
    fetchFestivals.mockRejectedValueOnce(new Error('timeout'))
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    expect(w.find('[data-test="festival-error"]').exists()).toBe(true)
    expect(w.text()).not.toContain('유등축제는 매년 10월')
    fetchFestivals.mockResolvedValueOnce({
      items: [{ id: 'a', title: '유등제', status: 'ongoing', start_date: '', end_date: '' }],
      today: '2026-10-05',
    })
    await w.find('[data-test="festival-error"] button').trigger('click')
    await flushPromises()
    expect(w.find('[data-test="festival-error"]').exists()).toBe(false)
    expect(w.text()).toContain('지금 진행 중: 유등제')
  })

  test('failed collection load shows – instead of 0 and offers retry', async () => {
    fetchFestivals.mockResolvedValue({ items: [], today: '2026-11-04' })
    const { fetchCollection } = await import('../../api/places')
    fetchCollection.mockRejectedValueOnce(new Error('timeout'))
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    expect(w.find('[data-test="progress-card"]').text()).toContain('–')
    expect(w.find('[data-test="progress-card"]').text()).not.toContain('◆ 0/')
    fetchCollection.mockResolvedValueOnce({ collection_ids: ['a', 'b'], badges: [] })
    await w.find('[data-test="progress-error"] button').trigger('click')
    await flushPromises()
    expect(w.find('[data-test="progress-card"]').text()).toContain('◆ 0/2')
  })
})
