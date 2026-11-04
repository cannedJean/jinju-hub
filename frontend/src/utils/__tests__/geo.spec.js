import { describe, expect, test } from 'vitest'
import { bboxToPoints, boundsToBbox, haversineMeters, radiusFitPoints } from '../geo'

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

describe('fit helpers', () => {
  test('radiusFitPoints spans the circle around the center', () => {
    const c = { lat: 35.18, lng: 128.108 }
    const [sw, ne] = radiusFitPoints(c, 1000)
    expect(sw.lat).toBeLessThan(c.lat)
    expect(ne.lng).toBeGreaterThan(c.lng)
    expect(Math.round(haversineMeters(c, { lat: ne.lat, lng: c.lng }))).toBe(1000)
    expect(Math.round(haversineMeters(c, { lat: c.lat, lng: ne.lng }))).toBe(1000)
  })

  test('bboxToPoints returns SW and NE corners', () => {
    expect(bboxToPoints('128.05,35.15,128.12,35.21')).toEqual([
      { lat: 35.15, lng: 128.05 },
      { lat: 35.21, lng: 128.12 },
    ])
    expect(bboxToPoints(null)).toBeNull()
  })
})
