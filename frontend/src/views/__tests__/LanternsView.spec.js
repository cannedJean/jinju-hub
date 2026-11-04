import { beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/places', () => ({
  fetchPlace: vi.fn(),
  fetchMarkers: vi.fn(() => Promise.resolve([])),
  fetchCollection: vi.fn(() =>
    Promise.resolve({
      collection_ids: ['jh-a', 'jh-b'],
      badges: [{ id: 'first_light', label: '첫 유등', description: '', required: 1 }],
    }),
  ),
}))
vi.mock('../../components/lanterns/LanternMap.vue', () => ({ default: { render: () => null } }))

import LanternsView from '../LanternsView.vue'
import { fetchCollection, fetchMarkers, fetchPlace } from '../../api/places'
import { useLanternsStore } from '../../stores/lanterns'
import { encodeShare } from '../../utils/share'

async function mountAt(path) {
  const Stub = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/lanterns', name: 'lanterns', component: LanternsView },
      { path: '/places/:id', name: 'place', component: Stub },
    ],
  })
  router.push(path)
  await router.isReady()
  const w = mount(LanternsView, { global: { plugins: [router] } })
  await flushPromises()
  return { w, router }
}

describe('LanternsView', () => {
  beforeEach(() => vi.clearAllMocks())

  test('missing place renders tombstone', async () => {
    fetchPlace.mockRejectedValue({ response: { status: 404 } })
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'jh-gone', title: '사라진 식당', category: 'food' })
    const { w } = await mountAt('/lanterns')
    expect(w.text()).toContain('더 이상 제공되지 않는 장소')
    const btn = w.findAll('button').find((b) => b.text().includes('빼기'))
    expect(btn).toBeTruthy()
    await btn.trigger('click')
    expect(lanterns.isSaved('jh-gone')).toBe(false)
  })

  test('saved item renders from snapshot with summary', async () => {
    fetchPlace.mockResolvedValue({ id: 'jh-a', title: '촉석루' })
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'jh-a', title: '촉석루', category: 'sight' })
    const { w } = await mountAt('/lanterns')
    expect(w.text()).toContain('촉석루')
    expect(w.text()).toContain('담음 1')
    expect(w.text()).not.toContain('더 이상 제공되지 않는 장소')
  })

  test('share query renders read-only banner', async () => {
    fetchPlace.mockImplementation((id) => Promise.resolve({ id, title: 'T' + id, category: 'sight' }))
    const { w } = await mountAt('/lanterns?share=' + encodeShare(['jh-a', 'jh-b']))
    expect(w.text()).toContain('공유받은 목록')
    expect(w.text()).toContain('Tjh-a')
    expect(w.text()).toContain('내 목록에 가져오기')
    expect(w.text()).not.toContain('빼기')
  })

  test('import adds to store and skips failed ids', async () => {
    fetchPlace.mockImplementation((id) =>
      id === 'jh-b'
        ? Promise.reject({ response: { status: 404 } })
        : Promise.resolve({ id, title: 'T' + id, category: 'sight', lat: 35.1, lng: 128.1 }),
    )
    const lanterns = useLanternsStore()
    const { w } = await mountAt('/lanterns?share=' + encodeShare(['jh-a', 'jh-b']))
    const btn = w.findAll('button').find((b) => b.text().includes('내 목록에 가져오기'))
    await btn.trigger('click')
    await flushPromises()
    expect(lanterns.isSaved('jh-a')).toBe(true)
    expect(lanterns.isSaved('jh-b')).toBe(false)
    expect(lanterns.items['jh-a'].title).toBe('Tjh-a')
  })

  test('warns when storage is unavailable', async () => {
    const lanterns = useLanternsStore()
    lanterns.storageAvailable = false
    const { w } = await mountAt('/lanterns')
    expect(w.text()).toContain('이 브라우저에서는 담은 목록이 저장되지 않아요')
  })

  test('share dialog shows url with encoded ids', async () => {
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'jh-a', title: 'A' })
    fetchPlace.mockResolvedValue({ id: 'jh-a', title: 'A' })
    const { w } = await mountAt('/lanterns')
    await w.findAll('button').find((b) => b.text().includes('공유')).trigger('click')
    const input = w.find('input[readonly]')
    expect(input.element.value).toContain('/lanterns?share=' + encodeShare(['jh-a']))
  })

  const removeBtn = (w) => w.findAll('button').find((b) => b.text().includes('빼기'))
  const litSave = () => {
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'jh-a', title: '촉석루', category: 'sight' })
    lanterns.light('jh-a', 'gps')
    return lanterns
  }

  test('remove then undo restores the lit record', async () => {
    fetchPlace.mockResolvedValue({ id: 'jh-a', title: '촉석루' })
    const lanterns = litSave()
    const litAt = lanterns.items['jh-a'].litAt
    const { w } = await mountAt('/lanterns')
    await removeBtn(w).trigger('click')
    expect(lanterns.isSaved('jh-a')).toBe(false)
    await w.findAll('button').find((b) => b.text().includes('실행 취소')).trigger('click')
    expect(lanterns.items['jh-a'].litAt).toBe(litAt)
    expect(lanterns.items['jh-a'].litMethod).toBe('gps')
  })

  test('remove then timeout keeps it removed', async () => {
    fetchPlace.mockResolvedValue({ id: 'jh-a', title: '촉석루' })
    const lanterns = litSave()
    const { w } = await mountAt('/lanterns')
    vi.useFakeTimers()
    try {
      await removeBtn(w).trigger('click')
      expect(w.text()).toContain('실행 취소')
      vi.advanceTimersByTime(5100)
      await nextTick()
      expect(w.text()).not.toContain('실행 취소')
      expect(lanterns.isSaved('jh-a')).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  test('tombstone checks respect the concurrency cap', async () => {
    const lanterns = useLanternsStore()
    for (let i = 0; i < 12; i++) lanterns.save({ id: `jh-${i}`, title: `T${i}` })
    let active = 0
    let max = 0
    fetchPlace.mockImplementation((id) => {
      active++
      max = Math.max(max, active)
      return new Promise((r) => setTimeout(() => (active--, r({ id })), 5))
    })
    await mountAt('/lanterns')
    await new Promise((r) => setTimeout(r, 100))
    expect(fetchPlace).toHaveBeenCalledTimes(12)
    expect(max).toBeLessThanOrEqual(4)
  })

  test('places present in markers are not fetched individually', async () => {
    fetchMarkers.mockResolvedValueOnce([{ id: 'jh-a', title: 'A', lat: 35.1, lng: 128.1, category: 'sight' }])
    useLanternsStore().save({ id: 'jh-a', title: 'A' })
    await mountAt('/lanterns')
    expect(fetchPlace).not.toHaveBeenCalled()
  })

  test('5xx is not a tombstone and is retried on the next visit', async () => {
    useLanternsStore().save({ id: 'jh-a', title: 'A' })
    fetchPlace.mockRejectedValueOnce({ response: { status: 503 } })
    const first = await mountAt('/lanterns')
    expect(first.w.text()).not.toContain('더 이상 제공되지 않는 장소')
    first.w.unmount()
    fetchPlace.mockResolvedValueOnce({ id: 'jh-a', title: 'A' })
    await mountAt('/lanterns')
    expect(fetchPlace).toHaveBeenCalledTimes(2)
  })

  test('collection load failure shows message and retry succeeds', async () => {
    fetchCollection.mockRejectedValueOnce(new Error('boom'))
    const { w } = await mountAt('/lanterns')
    expect(w.text()).toContain('배지 정보를 불러오지 못했어요')
    await w.findAll('button').find((b) => b.text().includes('다시 시도')).trigger('click')
    await flushPromises()
    expect(w.text()).not.toContain('배지 정보를 불러오지 못했어요')
  })

  test('retry after failed collection load awards badges', async () => {
    fetchCollection.mockRejectedValueOnce(new Error('boom'))
    litSave()
    const { w } = await mountAt('/lanterns')
    await w.findAll('button').find((b) => b.text().includes('다시 시도')).trigger('click')
    await flushPromises()
    expect(useLanternsStore().earnedBadges.first_light).toBeTruthy()
  })

  test('shared list with all fetches failing shows an error state', async () => {
    fetchPlace.mockRejectedValue({ response: { status: 500 } })
    const { w } = await mountAt('/lanterns?share=' + encodeShare(['jh-a']))
    expect(w.text()).toContain('공유받은 목록을 불러오지 못했어요')
  })
})
