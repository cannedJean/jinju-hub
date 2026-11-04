import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/places', () => ({
  fetchPlace: vi.fn(),
  fetchCollection: vi.fn(() =>
    Promise.resolve({
      collection_ids: ['jh-a', 'jh-b'],
      badges: [{ id: 'first_light', label: '첫 유등', description: '', required: 1 }],
    }),
  ),
}))
vi.mock('../../components/lanterns/LanternMap.vue', () => ({ default: { render: () => null } }))

import LanternsView from '../LanternsView.vue'
import { fetchPlace } from '../../api/places'
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
})
