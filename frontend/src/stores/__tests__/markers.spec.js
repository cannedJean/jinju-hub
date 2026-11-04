import { describe, expect, test, vi } from 'vitest'
import { useMarkersStore } from '../markers'
import * as placesApi from '../../api/places'

vi.mock('../../api/places', () => ({ fetchMarkers: vi.fn() }))

const DATA = [
  { id: 'a', lat: 35.19, lng: 128.08, category: 'food', title: 'A', is_collection: false },
  { id: 'b', lat: 35.18, lng: 128.09, category: 'sight', title: 'B', is_collection: true },
  { id: 'c', lat: 35.17, lng: 128.1, category: 'stay', title: 'C', is_collection: false },
]

describe('markers store', () => {
  test('load fetches once and shares concurrent calls', async () => {
    placesApi.fetchMarkers.mockReset().mockResolvedValue(DATA)
    const s = useMarkersStore()
    await Promise.all([s.load(), s.load()])
    await s.load()
    expect(placesApi.fetchMarkers).toHaveBeenCalledTimes(1)
    expect(s.items).toHaveLength(3)
    expect(s.byId.get('b').title).toBe('B')
  })

  test('byCategory filters; empty selection returns all', async () => {
    placesApi.fetchMarkers.mockReset().mockResolvedValue(DATA)
    const s = useMarkersStore()
    await s.load()
    expect(s.byCategory([]).map((m) => m.id)).toEqual(['a', 'b', 'c'])
    expect(s.byCategory(['food', 'stay']).map((m) => m.id)).toEqual(['a', 'c'])
    expect(s.counts).toEqual({ food: 1, sight: 1, stay: 1 })
  })

  test('failed load can be retried', async () => {
    placesApi.fetchMarkers.mockReset().mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce(DATA)
    const s = useMarkersStore()
    await expect(s.load()).rejects.toThrow('down')
    expect(s.error).toBe(true)
    await s.load()
    expect(s.error).toBe(false)
    expect(s.items).toHaveLength(3)
  })
})
