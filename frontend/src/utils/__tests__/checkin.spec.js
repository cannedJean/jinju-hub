import { afterEach, describe, expect, test, vi } from 'vitest'
import { LIGHT_RADIUS_M, MAX_ACCURACY_M, canLight, getPosition } from '../checkin'

const P = { lat: 35.1925, lng: 128.0845 }

describe('canLight', () => {
  test('constants', () => { expect(LIGHT_RADIUS_M).toBe(150); expect(MAX_ACCURACY_M).toBe(200) })
  test('ok within radius', () =>
    expect(canLight(P, { lat: 35.193, lng: 128.085, accuracy: 30 }).reason).toBe('ok'))
  test('rejects low accuracy even when at the place', () => {
    const r = canLight(P, { ...P, accuracy: 2000 })
    expect(r.reason).toBe('low_accuracy'); expect(r.ok).toBe(false)
  })
  test('accuracy exactly 200 is accepted at the place', () => expect(canLight(P, { ...P, accuracy: 200 }).ok).toBe(true))
  test('too far', () => {
    const r = canLight(P, { lat: 35.21, lng: 128.1, accuracy: 20 })
    expect(r.reason).toBe('too_far'); expect(r.distance).toBeGreaterThan(1000)
  })
  test('accuracy discounts distance', () => {
    const r = canLight(P, { lat: P.lat + 0.00198, lng: P.lng, accuracy: 100 })
    expect(r.distance).toBeGreaterThan(200); expect(r.ok).toBe(true)
  })
  test('no coords', () => {
    expect(canLight({ lat: null, lng: null }, { lat: 35, lng: 128, accuracy: 10 }).reason).toBe('no_coords')
    expect(canLight(null, { lat: 35, lng: 128, accuracy: 10 }).reason).toBe('no_coords')
  })
  test('missing accuracy is treated as low_accuracy', () =>
    expect(canLight(P, { ...P }).reason).toBe('low_accuracy'))
})

describe('getPosition', () => {
  afterEach(() => vi.unstubAllGlobals())
  const stub = (geo) => vi.stubGlobal('navigator', { geolocation: geo })
  test('unsupported', async () => {
    vi.stubGlobal('navigator', {})
    await expect(getPosition()).rejects.toThrow('unsupported')
  })
  test('resolves coords', async () => {
    stub({ getCurrentPosition: (ok) => ok({ coords: { latitude: 1, longitude: 2, accuracy: 3 } }) })
    await expect(getPosition()).resolves.toEqual({ lat: 1, lng: 2, accuracy: 3 })
  })
  test('permission denied', async () => {
    stub({ getCurrentPosition: (_ok, err) => err({ code: 1, PERMISSION_DENIED: 1 }) })
    await expect(getPosition()).rejects.toThrow('permission_denied')
  })
  test('other errors', async () => {
    stub({ getCurrentPosition: (_ok, err) => err({ code: 3, PERMISSION_DENIED: 1 }) })
    await expect(getPosition()).rejects.toThrow('position_unavailable')
  })
})
