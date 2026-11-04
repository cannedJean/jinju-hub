import { describe, expect, test, vi } from 'vitest'
import { useFestivalsStore } from '../festivals'
import { useLanternsStore } from '../lanterns'
import * as api from '../../api/places'

vi.mock('../../api/places', () => ({ fetchFestivals: vi.fn() }))

const ITEMS = [
  { id: 'a', status: 'ongoing' },
  { id: 'b', status: 'upcoming' },
  { id: 'c', status: 'ended' },
  { id: 'd', status: 'stale' },
  { id: 'e', status: 'undecided' },
]

describe('festivals store', () => {
  test('demo mode sends today', async () => {
    api.fetchFestivals.mockResolvedValue({ today: '2026-10-10', items: ITEMS })
    useLanternsStore().setDemo({ enabled: true, today: '2026-10-10', pos: null })
    await useFestivalsStore().load()
    expect(api.fetchFestivals).toHaveBeenLastCalledWith({ status: 'all', today: '2026-10-10' })
  })

  test('non-demo omits today', async () => {
    api.fetchFestivals.mockResolvedValue({ today: '2026-11-04', items: [] })
    await useFestivalsStore().load()
    expect(api.fetchFestivals).toHaveBeenLastCalledWith({ status: 'all', today: undefined })
  })

  test('groups by status', async () => {
    api.fetchFestivals.mockResolvedValue({ today: 'x', items: ITEMS })
    const s = useFestivalsStore()
    await s.load()
    expect(s.ongoing.map((f) => f.id)).toEqual(['a'])
    expect(s.upcoming.map((f) => f.id)).toEqual(['b'])
    expect(s.past.map((f) => f.id)).toEqual(['c', 'd', 'e'])
  })

  test('failure sets error', async () => {
    api.fetchFestivals.mockRejectedValue(new Error('x'))
    const s = useFestivalsStore()
    await s.load()
    expect(s.error).toBe(true)
    expect(s.loading).toBe(false)
  })
})
