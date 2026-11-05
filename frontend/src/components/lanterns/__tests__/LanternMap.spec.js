import { afterEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import L from 'leaflet'
import LanternMap from '../LanternMap.vue'
import MapCanvas from '../../map/MapCanvas.vue'

const items = [
  { id: 'jh-a', title: 'A', category: 'sight', lat: 35.19, lng: 128.08 },
  { id: 'jh-b', title: 'B', category: 'food', lat: 35.3, lng: 128.2 },
]
const router = () => createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })

describe('LanternMap', () => {
  afterEach(() => vi.restoreAllMocks())

  test('passes fitTo as {lat,lng} objects', () => {
    const w = mount(LanternMap, { props: { items }, global: { plugins: [router()], stubs: { MapCanvas: true } } })
    expect(w.findComponent(MapCanvas).props('fitTo')).toEqual([
      { lat: 35.19, lng: 128.08 },
      { lat: 35.3, lng: 128.2 },
    ])
  })

  test('the real MapCanvas fits the map to the user places', async () => {
    const fit = vi.spyOn(L.Map.prototype, 'fitBounds')
    const w = mount(LanternMap, { props: { items }, global: { plugins: [router()] }, attachTo: document.body })
    await flushPromises()
    expect(fit).toHaveBeenCalledTimes(1)
    w.unmount()
  })
})
