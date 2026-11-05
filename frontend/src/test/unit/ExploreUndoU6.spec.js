import { describe, expect, test, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ExploreView from '../../views/ExploreView.vue'
import { useLanternsStore } from '../../stores/lanterns'

vi.mock('../../components/map/MapCanvas.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      props: { markers: { type: Array, default: () => [] } },
      setup(props, { expose }) {
        expose({ focusMarker: () => false, closePopup: () => {} })
        return () => h('div', { 'data-test': 'map' })
      },
    }),
  }
})
vi.mock('../../api/places', () => ({
  fetchPlaces: vi.fn(() => Promise.resolve({ items: [], total: 0, page: 1, totalPages: 0 })),
  fetchMarkers: vi.fn(() => Promise.resolve([])),
  fetchPlace: vi.fn(),
}))
vi.mock('../../api/weather', () => ({
  fetchWeather: vi.fn(() => Promise.resolve({})),
}))

function desktop() {
  window.matchMedia = vi.fn((query) => ({
    matches: query === '(min-width: 1280px)',
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }))
}

describe('U6 - Lantern Toggle Undo Toast in ExploreView', () => {
  let router

  beforeEach(() => {
    desktop()
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/explore', name: 'explore', component: ExploreView },
        { path: '/places/:id', name: 'place', component: { template: '<div />' } },
      ],
    })
  })

  test('ExploreView displays undo button on unsave and restores lantern upon clicking undo', async () => {
    const lanterns = useLanternsStore()
    lanterns.save({
      id: 'jh-chokseok',
      title: '촉석루',
      category: 'sight',
      lat: 35.18,
      lng: 128.08,
    })
    expect(lanterns.isSaved('jh-chokseok')).toBe(true)

    await router.push('/explore')
    await router.isReady()
    const wrapper = mount(ExploreView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    // Trigger toggleSave to unsave
    wrapper.vm.toggleSave('jh-chokseok')
    await flushPromises()

    // Place should now be unsaved
    expect(lanterns.isSaved('jh-chokseok')).toBe(false)

    // Undo toast button must exist
    const undoBtn = wrapper.find('[data-test="toast-undo"]')
    expect(undoBtn.exists()).toBe(true)
    expect(undoBtn.text()).toContain('실행 취소')

    // Click undo button
    await undoBtn.trigger('click')
    await flushPromises()

    // Place must be restored in lanterns store
    expect(lanterns.isSaved('jh-chokseok')).toBe(true)
    expect(lanterns.items['jh-chokseok'].title).toBe('촉석루')
    wrapper.unmount()
  })
})
