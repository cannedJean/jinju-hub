import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LanternMap from '../LanternMap.vue'
import MapCanvas from '../../map/MapCanvas.vue'

describe('LanternMap', () => {
  test('passes fitTo as {lat,lng} objects so MapCanvas can frame the user places', () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
    const w = mount(LanternMap, {
      props: {
        items: [
          { id: 'jh-a', title: 'A', category: 'sight', lat: 35.19, lng: 128.08 },
          { id: 'jh-b', title: 'B', category: 'food', lat: 35.3, lng: 128.2 },
        ],
      },
      global: { plugins: [router], stubs: { MapCanvas: true } },
    })
    const fit = w.findComponent(MapCanvas).props('fitTo')
    expect(fit).toEqual([
      { lat: 35.19, lng: 128.08 },
      { lat: 35.3, lng: 128.2 },
    ])
  })
})
