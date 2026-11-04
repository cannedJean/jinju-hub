import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/places', () => ({
  fetchPlace: vi.fn(),
  fetchCollection: vi.fn(() => Promise.resolve({ collection_ids: [], badges: [] })),
}))
vi.mock('../../components/place/MiniMap.vue', () => ({ __esModule: true, default: { render: () => null } }))

import PlaceDetailView from '../PlaceDetailView.vue'
import { fetchPlace } from '../../api/places'
import { useLanternsStore } from '../../stores/lanterns'

function makeRouter() {
  const Stub = { template: '<div />' }
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/places/:id', name: 'place', component: PlaceDetailView },
      { path: '/explore', name: 'explore', component: Stub },
    ],
  })
}

async function mountAt(path) {
  const router = makeRouter()
  router.push(path)
  await router.isReady()
  const w = mount(PlaceDetailView, { global: { plugins: [router] } })
  await flushPromises()
  return { w, router }
}

const detail = { id: 'p1', canonical_id: 'p1', category: 'sight', title: '촉석루', lat: 35.19, lng: 128.08, images: [], nearby: [], sources: [] }

describe('PlaceDetailView', () => {
  beforeEach(() => vi.clearAllMocks())

  test('renders place', async () => {
    fetchPlace.mockResolvedValue(detail)
    const { w } = await mountAt('/places/p1')
    expect(w.text()).toContain('촉석루')
    expect(w.text()).toContain('유등 띄우기')
  })

  test('404 shows tombstone with saved snapshot title and removal', async () => {
    fetchPlace.mockRejectedValue({ response: { status: 404 } })
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'gone', title: '사라진 식당', category: 'food' })
    const { w } = await mountAt('/places/gone')
    expect(w.text()).toContain('더 이상 제공되지 않는 장소예요')
    expect(w.text()).toContain('사라진 식당')
    await w.find('button').trigger('click')
    expect(lanterns.isSaved('gone')).toBe(false)
  })

  test('alias migrates saved id and replaces route', async () => {
    const lanterns = useLanternsStore()
    lanterns.save({ id: 'old', title: '옛 이름' })
    fetchPlace.mockImplementation((id) =>
      Promise.resolve(id === 'old' ? { ...detail, id: 'new', canonical_id: 'new' } : { ...detail, id: 'new', canonical_id: 'new' }),
    )
    const { router } = await mountAt('/places/old')
    expect(router.currentRoute.value.params.id).toBe('new')
    expect(lanterns.isSaved('new')).toBe(true)
    expect(lanterns.isSaved('old')).toBe(false)
  })
})
