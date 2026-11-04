import { describe, expect, test } from 'vitest'
import { boundsToBbox, haversineMeters } from '../geo'

describe('geo', () => {
  test('haversine 진주성↔촉석루 < 400m', () =>
    expect(haversineMeters({ lat: 35.1925, lng: 128.0845 }, { lat: 35.1897, lng: 128.0819 })).toBeLessThan(400))
  test('haversine same point is 0', () =>
    expect(haversineMeters({ lat: 35, lng: 128 }, { lat: 35, lng: 128 })).toBe(0))
  test('boundsToBbox formats minLng,minLat,maxLng,maxLat with 5 decimals', () => {
    const b = { getWest: () => 128.0, getSouth: () => 35.1, getEast: () => 128.123456789, getNorth: () => 35.2 }
    expect(boundsToBbox(b)).toBe('128.00000,35.10000,128.12346,35.20000')
  })
})
