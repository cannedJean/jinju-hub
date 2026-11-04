import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { getActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ExploreView from '../ExploreView.vue'
import * as placesApi from '../../api/places'
import { useLanternsStore } from '../../stores/lanterns'

// Leaflet is not rendered in jsdom: the map is a stub that exposes the markers it receives.
vi.mock('../../components/map/MapCanvas.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      props: { markers: { type: Array, default: () => [] } },
      setup(props, { expose }) {
        expose({ focusMarker: () => false, closePopup: () => {} })
        return () => h('div', { 'data-test': 'map', 'data-ids': props.markers.map((m) => m.id).join(',') })
      },
    }),
  }
})
vi.mock('../../api/places', () => ({ fetchPlaces: vi.fn(), fetchMarkers: vi.fn(), fetchPlace: vi.fn() }))
vi.mock('../../api/weather', () => ({ fetchWeather: vi.fn(() => Promise.reject(new Error('offline'))) }))

const MARKERS = [
  { id: 'a', lat: 35.19, lng: 128.08, category: 'food', title: 'A', is_collection: false },
  { id: 'b', lat: 35.18, lng: 128.09, category: 'sight', title: 'B', is_collection: false },
]
const PAGE = { items: [], total: 0, page: 1, totalPages: 0 }

function desktop() {
  window.matchMedia = vi.fn((query) => ({
    matches: query === '(min-width: 1280px)',
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }))
}

async function mountAt(path) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/explore', name: 'explore', component: ExploreView },
      { path: '/places/:id', name: 'place', component: { render: () => null } },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(ExploreView, { global: { plugins: [router, getActivePinia()] } })
  await flushPromises()
  return wrapper
}

const mapIds = (w) => w.get('[data-test="map"]').attributes('data-ids').split(',').filter(Boolean)

describe('ExploreView', () => {
  beforeEach(() => {
    desktop()
    placesApi.fetchPlaces.mockReset().mockResolvedValue(PAGE)
    placesApi.fetchMarkers.mockReset()
  })

  test('marker load failure shows a retry overlay that reloads the markers', async () => {
    placesApi.fetchMarkers.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce(MARKERS)
    const w = await mountAt('/explore')
    const overlay = w.find('[data-test="markers-error"]')
    expect(overlay.exists()).toBe(true)
    expect(overlay.text()).toContain('다시 시도')

    await overlay.get('button').trigger('click')
    await flushPromises()
    expect(placesApi.fetchMarkers).toHaveBeenCalledTimes(2)
    expect(w.find('[data-test="markers-error"]').exists()).toBe(false)
    expect(mapIds(w)).toEqual(['a', 'b'])
  })

  test('the list retry also retries failed markers', async () => {
    placesApi.fetchPlaces.mockReset().mockRejectedValueOnce(new Error('down')).mockResolvedValue(PAGE)
    placesApi.fetchMarkers.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce(MARKERS)
    const w = await mountAt('/explore')
    const retry = w.findAll('button').find((b) => b.text() === '다시 시도' && !b.element.closest('[data-test="markers-error"]'))
    await retry.trigger('click')
    await flushPromises()
    expect(placesApi.fetchPlaces).toHaveBeenCalledTimes(2)
    expect(placesApi.fetchMarkers).toHaveBeenCalledTimes(2)
    expect(w.find('[data-test="markers-error"]').exists()).toBe(false)
  })

  test('saved places stay on the map outside the category filter and in search mode', async () => {
    placesApi.fetchMarkers.mockResolvedValue(MARKERS)
    useLanternsStore().save({ id: 'b', title: 'B', category: 'sight', lat: 35.18, lng: 128.09 })

    const filtered = await mountAt('/explore?cat=food')
    expect(mapIds(filtered)).toEqual(['a', 'b'])
    filtered.unmount()

    const searching = await mountAt('/explore?q=냉면')
    expect(mapIds(searching)).toEqual(['b'])
  })
})
