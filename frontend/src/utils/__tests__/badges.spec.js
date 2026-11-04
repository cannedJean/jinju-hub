import { describe, expect, test } from 'vitest'
import { evaluateBadges } from '../badges'

const byId = (arr) => Object.fromEntries(arr.map((b) => [b.id, b]))
function stateLit(ids, litOn = '2026-10-10', extraSaved = []) {
  const items = {}
  for (const id of ids) items[id] = { id, litAt: litOn + 'T00:00:00Z', litOn }
  for (const id of extraSaved) items[id] = { id, savedAt: 'x' }
  return { items }
}
function coll(over = {}) {
  const el = (id) => over[id] || []
  return {
    badges: [
      { id: 'first_light', required: 1, eligible_place_ids: [], festival_windows: [] },
      { id: 'jinju8', required: 8, eligible_place_ids: el('jinju8'), festival_windows: [] },
      { id: 'food_explorer', required: 3, eligible_place_ids: el('food_explorer'), festival_windows: [] },
      { id: 'history_walk', required: 3, eligible_place_ids: el('history_walk'), festival_windows: [] },
      { id: 'night_namgang', required: 3, eligible_place_ids: el('night_namgang'), festival_windows: [] },
      { id: 'festival_guest', required: 1, eligible_place_ids: [], festival_windows: over.festival_windows || [] },
    ],
  }
}

describe('evaluateBadges', () => {
  test('jinju8 progress counts only lit eligible', () => {
    const r = byId(evaluateBadges(stateLit(['a', 'b', 'x']), coll({ jinju8: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] })))
    expect(r.jinju8).toMatchObject({ progress: 2, required: 8, earned: false })
  })
  test('saved-but-unlit does not count', () => {
    const r = byId(evaluateBadges(stateLit(['a'], '2026-10-10', ['b']), coll({ jinju8: ['a', 'b'] })))
    expect(r.jinju8.progress).toBe(1)
  })
  test('first_light counts lit total and earns at 1', () => {
    expect(byId(evaluateBadges(stateLit([]), coll())).first_light).toMatchObject({ progress: 0, earned: false })
    expect(byId(evaluateBadges(stateLit(['z']), coll())).first_light).toMatchObject({ progress: 1, earned: true })
  })
  test('food_explorer earns at required', () => {
    const r = byId(evaluateBadges(stateLit(['a', 'b', 'c']), coll({ food_explorer: ['a', 'b', 'c', 'd'] })))
    expect(r.food_explorer.earned).toBe(true)
  })
  test('festival_guest requires litOn within window', () => {
    const c = coll({ festival_windows: [{ festival_id: 'f', start: '2026-10-03', end: '2026-10-18', venue_place_ids: ['v'] }] })
    expect(byId(evaluateBadges(stateLit(['v'], '2026-10-10'), c)).festival_guest.earned).toBe(true)
    expect(byId(evaluateBadges(stateLit(['v'], '2026-11-04'), c)).festival_guest.earned).toBe(false)
    expect(byId(evaluateBadges(stateLit(['other'], '2026-10-10'), c)).festival_guest.earned).toBe(false)
  })
  test('required 0 or missing is treated as at least 1', () => {
    const c = { badges: [{ id: 'jinju8', required: 0, eligible_place_ids: ['a'] }, { id: 'food_explorer', eligible_place_ids: ['a'] }] }
    const r = byId(evaluateBadges(stateLit([]), c))
    expect(r.jinju8).toMatchObject({ required: 1, earned: false })
    expect(r.food_explorer.earned).toBe(false)
  })
  test('handles empty/missing collection', () => {
    expect(evaluateBadges({ items: {} }, null)).toEqual([])
    expect(evaluateBadges({ items: {} }, {})).toEqual([])
  })
})
