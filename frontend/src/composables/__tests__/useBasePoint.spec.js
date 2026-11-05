import { describe, expect, test, vi } from 'vitest'
import { computed, effectScope, ref } from 'vue'
import { useBasePoint } from '../useBasePoint'
import { parseQuery } from '../useExploreQuery'
import { useLanternsStore } from '../../stores/lanterns'
import { DEMO_START } from '../../utils/geo'

// Runs the composable inside an effect scope (stand-in for a component) with a fake URL state.
function setup({ query = {}, geolocation } = {}) {
  const route = ref(parseQuery(query))
  const state = computed(() => route.value)
  const update = vi.fn((patch) => {
    route.value = { ...route.value, page: 1, ...patch }
  })
  const onBaseSet = vi.fn()
  const scope = effectScope()
  const api = scope.run(() => useBasePoint({ state, update, onBaseSet, geolocation }))
  return { api, update, onBaseSet, scope, lanterns: useLanternsStore(), state }
}

// Fake geolocation whose callbacks the test fires by hand.
function fakeGeo() {
  const calls = []
  return {
    calls,
    getCurrentPosition: (ok, fail) => calls.push({ ok, fail }),
  }
}

const JINJU = { latitude: 35.19, longitude: 128.08, accuracy: 20 }

describe('useBasePoint', () => {
  test('setBase stores the lodging and applies near/radius/sort=distance', () => {
    const { api, update, onBaseSet, lanterns } = setup({ query: { bbox: '128.05,35.15,128.12,35.21' } })
    api.setBase({ lat: 35.19, lng: 128.08, label: '호텔' })
    expect(lanterns.base).toEqual({ lat: 35.19, lng: 128.08, label: '호텔' })
    expect(update).toHaveBeenCalledWith({ near: { lat: 35.19, lng: 128.08 }, radius: 1000, sort: 'distance', bbox: null })
    expect(onBaseSet).toHaveBeenCalledWith({ lat: 35.19, lng: 128.08, label: '호텔' })
    expect(api.refPoint.value).toMatchObject({ lat: 35.19, lng: 128.08, label: '호텔' })
    expect(api.activeRadius.value).toBe(1000)
  })

  test('refPoint falls back to the stored lodging; a foreign URL point is labelled 기준점', () => {
    const a = setup()
    a.lanterns.setBase({ lat: 35.2, lng: 128.1, label: '내 호텔' })
    expect(a.api.refPoint.value).toEqual({ lat: 35.2, lng: 128.1, label: '내 호텔' })
    expect(a.api.activeRadius.value).toBeNull()

    const b = setup({ query: { near: '35.17,128.12', radius: '500' } })
    expect(b.api.refPoint.value).toEqual({ lat: 35.17, lng: 128.12, label: '기준점' })
  })

  test('setRadius applies or removes the radius around the reference point', () => {
    const { api, update, lanterns } = setup()
    lanterns.setBase({ lat: 35.2, lng: 128.1, label: '내 호텔' })
    api.setRadius(3000)
    expect(update).toHaveBeenLastCalledWith({ near: { lat: 35.2, lng: 128.1 }, radius: 3000, sort: 'distance', bbox: null })
    api.setRadius(null)
    expect(update).toHaveBeenLastCalledWith({ near: null, radius: null })
  })

  test('clearBase forgets the lodging and leaves distance sort', () => {
    const { api, update, lanterns } = setup()
    api.setBase({ lat: 35.19, lng: 128.08, label: '호텔' })
    api.clearBase()
    expect(lanterns.base).toBeNull()
    expect(update).toHaveBeenLastCalledWith({ near: null, radius: null, sort: 'relevance' })
  })

  test('pickAt ignores points outside the Jinju bounds', () => {
    const { api, update } = setup()
    api.startPicking()
    expect(api.picking.value).toBe(true)
    api.pickAt({ lat: 37.5, lng: 127 })
    expect(update).not.toHaveBeenCalled()
    api.pickAt({ lat: 35.18, lng: 128.1 })
    expect(api.picking.value).toBe(false)
    expect(update).toHaveBeenCalledTimes(1)
  })

  test('locate sets the base from GPS and warns about low accuracy', () => {
    const geo = fakeGeo()
    const { api, lanterns } = setup({ geolocation: geo })
    api.locate()
    expect(api.locating.value).toBe(true)
    geo.calls[0].ok({ coords: { ...JINJU, accuracy: 1500 } })
    expect(api.locating.value).toBe(false)
    expect(lanterns.base).toMatchObject({ lat: 35.19, lng: 128.08, label: '현재 위치' })
    expect(api.message.value).toContain('정확도가 낮아요')
  })

  test('locate explains permission denial and positions outside Jinju', () => {
    const geo = fakeGeo()
    const { api, lanterns } = setup({ geolocation: geo })
    api.locate()
    geo.calls[0].fail({ code: 1 })
    expect(api.message.value).toContain('권한이 거부')
    api.locate()
    geo.calls[1].ok({ coords: { latitude: 37.5, longitude: 127, accuracy: 10 } })
    expect(api.message.value).toContain('진주 밖')
    expect(lanterns.base).toBeNull()
  })

  test('locate without geolocation support asks to pick on the map', () => {
    const { api } = setup({ geolocation: null })
    api.locate()
    expect(api.message.value).toContain('지원하지 않아요')
  })

  test('demo mode uses the virtual position instead of GPS', () => {
    const geo = fakeGeo()
    const { api, lanterns } = setup({ geolocation: geo })
    lanterns.setDemo({ enabled: true, today: null, pos: { lat: 35.18, lng: 128.09 } })
    api.locate()
    expect(geo.calls).toHaveLength(0)
    expect(lanterns.base).toMatchObject({ lat: 35.18, lng: 128.09, label: '가상 내 위치' })
  })

  test('demo mode with no dragged pin still uses the displayed default pin (촉석루), not GPS', () => {
    const geo = fakeGeo()
    const { api, lanterns } = setup({ geolocation: geo })
    lanterns.setDemo({ enabled: true, today: null, pos: null })
    api.locate()
    expect(geo.calls).toHaveLength(0)
    expect(lanterns.base).toMatchObject({ lat: DEMO_START.lat, lng: DEMO_START.lng, label: '가상 내 위치' })
  })

  test('a position arriving after unmount is ignored (no navigation, base untouched)', () => {
    const geo = fakeGeo()
    const { api, update, lanterns, scope } = setup({ geolocation: geo })
    api.locate()
    scope.stop()
    geo.calls[0].ok({ coords: JINJU })
    expect(update).not.toHaveBeenCalled()
    expect(lanterns.base).toBeNull()

    api.locate() // a stopped scope never starts new requests either
    expect(geo.calls).toHaveLength(1)
  })

  test('an error arriving after unmount is ignored', () => {
    const geo = fakeGeo()
    const { api, scope } = setup({ geolocation: geo })
    api.locate()
    scope.stop()
    geo.calls[0].fail({ code: 1 })
    expect(api.message.value).toBe('')
  })
})
