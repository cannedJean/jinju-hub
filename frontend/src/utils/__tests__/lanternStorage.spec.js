import { describe, expect, test } from 'vitest'
import { STORAGE_KEY, emptyState, loadState, saveState } from '../lanternStorage'

function fakeStorage(init = {}) {
  const m = { ...init }
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v) }, m }
}

describe('lanternStorage', () => {
  test('key', () => expect(STORAGE_KEY).toBe('jinjuhub.lanterns.v1'))
  test('emptyState shape', () =>
    expect(emptyState()).toEqual({ version: 1, items: {}, base: null, demo: { enabled: false, today: null, pos: null }, earnedBadges: {} }))
  test('loadState returns empty when missing', () => expect(loadState(fakeStorage())).toEqual(emptyState()))
  test('loadState falls back on corrupted json', () => {
    const s = fakeStorage({ 'jinjuhub.lanterns.v1': '{oops' })
    expect(loadState(s)).toEqual(emptyState())
  })
  test('loadState falls back when storage throws', () =>
    expect(loadState({ getItem() { throw new Error('SecurityError') } })).toEqual(emptyState()))
  test('loadState falls back on version mismatch', () => {
    const s = fakeStorage({ [STORAGE_KEY]: JSON.stringify({ version: 2, items: { a: {} } }) })
    expect(loadState(s)).toEqual(emptyState())
  })
  test('loadState falls back on non-object json', () =>
    expect(loadState(fakeStorage({ [STORAGE_KEY]: 'null' }))).toEqual(emptyState()))
  test('loadState tolerates missing optional fields', () => {
    const s = fakeStorage({ [STORAGE_KEY]: JSON.stringify({ version: 1, items: { a: { id: 'a' } } }) })
    const st = loadState(s)
    expect(st.items.a.id).toBe('a')
    expect(st.demo).toEqual({ enabled: false, today: null, pos: null })
    expect(st.earnedBadges).toEqual({})
  })
  test('save then load roundtrip', () => {
    const s = fakeStorage()
    const st = { ...emptyState(), base: { lat: 1, lng: 2, label: 'x' } }
    expect(saveState(st, s)).toBe(true)
    expect(loadState(s)).toEqual(st)
  })
  test('saveState swallows quota errors', () =>
    expect(saveState(emptyState(), { setItem() { throw new DOMException('quota') } })).toBe(false))
})
