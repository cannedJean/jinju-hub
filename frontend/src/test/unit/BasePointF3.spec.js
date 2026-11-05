import { describe, expect, test, vi, beforeEach } from 'vitest'
import { computed, effectScope, ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useBasePoint } from '../../composables/useBasePoint'
import { useLanternsStore } from '../../stores/lanterns'
import MapCanvas from '../../components/map/MapCanvas.vue'

function setupBasePoint() {
  const route = ref({ near: null, radius: null })
  const state = computed(() => route.value)
  const update = vi.fn()
  const scope = effectScope()
  const api = scope.run(() => useBasePoint({ state, update, onBaseSet: vi.fn(), geolocation: null }))
  return { api, lanterns: useLanternsStore() }
}

describe('Base Point & Map Tooltip F3', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
  })

  test('demo mode locate sets base label to "내 숙소 (가상 위치)"', () => {
    const { api, lanterns } = setupBasePoint()
    lanterns.setDemo({ enabled: true, today: null, pos: { lat: 35.18, lng: 128.09 } })
    api.locate()
    expect(lanterns.base.label).toBe('내 숙소 (가상 위치)')
  })

  test('MapCanvas avoids duplicate stacked permanent tooltip when base equals virtualPos', async () => {
    const pos = { lat: 35.18, lng: 128.09 }
    const w = mount(MapCanvas, {
      props: {
        base: { ...pos, label: '내 숙소 (가상 위치)' },
        virtualPos: { ...pos },
        markers: [],
      },
      global: { plugins: [router] },
      attachTo: document.body,
    })
    await flushPromises()

    // Virtual tooltip exists
    const virtualTooltips = document.querySelectorAll('.jh-virtual-tooltip')
    expect(virtualTooltips.length).toBe(1)

    // Base tooltip should be suppressed on the exact same coordinate to prevent stacked duplicates
    const baseTooltips = document.querySelectorAll('.jh-base-tooltip')
    expect(baseTooltips.length).toBe(0)

    w.unmount()
  })

  test('MapCanvas renders base tooltip when base differs from virtualPos', async () => {
    const w = mount(MapCanvas, {
      props: {
        base: { lat: 35.19, lng: 128.08, label: '내 숙소 (호텔)' },
        virtualPos: { lat: 35.18, lng: 128.09 },
        markers: [],
      },
      global: { plugins: [router] },
      attachTo: document.body,
    })
    await flushPromises()

    const baseTooltips = document.querySelectorAll('.jh-base-tooltip')
    expect(baseTooltips.length).toBe(1)
    expect(baseTooltips[0].textContent).toContain('내 숙소 (호텔)')

    w.unmount()
  })
})
