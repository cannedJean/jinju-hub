import { beforeEach, describe, expect, test, vi } from 'vitest'
import { STORAGE_KEY } from '../../utils/lanternStorage'
import { useLanternsStore } from '../lanterns'
import { useCollectionStore } from '../collection'
import * as placesApi from '../../api/places'

vi.mock('../../api/places', () => ({ fetchCollection: vi.fn() }))

const P = { id: 'jh-1', title: '촉석루', category: 'sight', tags: ['night_view'], lat: 35.19, lng: 128.08 }

describe('lanterns store', () => {
  test('light auto-saves with snapshot and stamps demo date', () => {
    const s = useLanternsStore()
    s.setDemo({ enabled: true, today: '2026-10-10', pos: null })
    s.light('jh-1', 'demo', P)
    expect(s.items['jh-1']).toMatchObject({ title: '촉석루', category: 'sight', litOn: '2026-10-10', litMethod: 'demo' })
    expect(s.isLit('jh-1') && s.isSaved('jh-1')).toBe(true)
    expect(s.litCount).toBe(1)
  })
  test('light without summary makes minimal snapshot', () => {
    const s = useLanternsStore()
    s.light('jh-9', 'gps')
    expect(s.items['jh-9']).toMatchObject({ id: 'jh-9', title: 'jh-9', litMethod: 'gps' })
  })
  test('effectiveToday uses KST by default and demo when enabled', () => {
    const s = useLanternsStore()
    expect(s.effectiveToday).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    s.setDemo({ enabled: true, today: '2026-10-10', pos: null })
    expect(s.effectiveToday).toBe('2026-10-10')
    s.setDemo({ enabled: true, today: null, pos: null })
    expect(s.effectiveToday).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
  test('save/unsave and savedList ordering', () => {
    const s = useLanternsStore()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z')); s.save({ ...P, id: 'a' })
    vi.setSystemTime(new Date('2026-01-02T00:00:00Z')); s.save({ ...P, id: 'b' })
    vi.useRealTimers()
    expect(s.savedList.map((x) => x.id)).toEqual(['b', 'a'])
    s.unsave('a')
    expect(s.isSaved('a')).toBe(false)
  })
  test('re-saving keeps lit state', () => {
    const s = useLanternsStore()
    s.light('jh-1', 'gps', P); s.save(P)
    expect(s.isLit('jh-1')).toBe(true)
  })
  test('migrateId moves state', () => {
    const s = useLanternsStore()
    s.save({ ...P, id: 'jh-old' }); s.migrateId('jh-old', 'jh-new')
    expect(s.isSaved('jh-new') && !s.isSaved('jh-old')).toBe(true)
    expect(s.items['jh-new'].id).toBe('jh-new')
    s.migrateId('nope', 'x')
    expect(s.isSaved('x')).toBe(false)
  })
  test('migrateId does not overwrite an existing new id', () => {
    const s = useLanternsStore()
    s.light('jh-new', 'gps', { ...P, id: 'jh-new' }); s.save({ ...P, id: 'jh-old' })
    s.migrateId('jh-old', 'jh-new')
    expect(s.isLit('jh-new')).toBe(true)
    expect(s.isSaved('jh-old')).toBe(false)
  })
  test('importShared saves unknown ids, keeps existing', () => {
    const s = useLanternsStore()
    s.light('jh-1', 'gps', P)
    s.importShared(['jh-1', 'jh-2'], { 'jh-2': { ...P, id: 'jh-2', title: 'B' } })
    expect(s.isLit('jh-1')).toBe(true)
    expect(s.items['jh-2'].title).toBe('B')
  })
  test('setBase', () => {
    const s = useLanternsStore()
    s.setBase({ lat: 1, lng: 2, label: 'x' }); expect(s.base.label).toBe('x')
    s.setBase(null); expect(s.base).toBeNull()
  })
  test('persists to localStorage without storageAvailable', () => {
    const s = useLanternsStore(); s.save(P)
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY))
    expect(raw.items['jh-1'].title).toBe('촉석루')
    expect('storageAvailable' in raw).toBe(false)
    expect(s.storageAvailable).toBe(true)
  })
  test('storage failure flags storageAvailable=false but keeps memory state', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('quota') })
    const s = useLanternsStore(); s.save(P)
    expect(s.storageAvailable).toBe(false)
    expect(s.isSaved('jh-1')).toBe(true)
    spy.mockRestore()
  })
  test('loads existing state from localStorage', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, items: { x: { id: 'x', litAt: 'a', litOn: '2026-01-01' } } }))
    expect(useLanternsStore().isLit('x')).toBe(true)
  })
  test('corrupted localStorage does not crash', () => {
    localStorage.setItem(STORAGE_KEY, '{oops')
    expect(useLanternsStore().litCount).toBe(0)
  })
})

describe('collection store', () => {
  const data = {
    collection_ids: ['a', 'b'],
    jinju8: [],
    badges: [
      { id: 'first_light', label: 'F', description: '', required: 1, eligible_place_ids: [], festival_windows: [] },
      { id: 'jinju8', label: 'J', description: '', required: 2, eligible_place_ids: ['a', 'b'], festival_windows: [] },
    ],
    places: [],
  }
  beforeEach(() => { placesApi.fetchCollection.mockReset(); placesApi.fetchCollection.mockResolvedValue(data) })

  test('load caches a single fetch', async () => {
    const c = useCollectionStore()
    await Promise.all([c.load(), c.load()]); await c.load()
    expect(placesApi.fetchCollection).toHaveBeenCalledTimes(1)
    expect(c.collectionIds).toEqual(['a', 'b'])
  })
  test('load failure can be retried', async () => {
    placesApi.fetchCollection.mockRejectedValueOnce(new Error('net'))
    const c = useCollectionStore()
    await expect(c.load()).rejects.toThrow('net')
    await c.load()
    expect(c.collectionIds).toEqual(['a', 'b'])
  })
  test('progress = lit ∩ collectionIds', async () => {
    const c = useCollectionStore(); await c.load()
    const l = useLanternsStore()
    l.light('a', 'gps'); l.light('zzz', 'gps')
    expect(c.progress).toBe(1)
  })
  test('newly earned badges queue once and persist', async () => {
    const c = useCollectionStore(); await c.load()
    const l = useLanternsStore()
    l.light('a', 'gps')
    c.checkBadges()
    expect(c.newlyEarned.map((b) => b.id)).toEqual(['first_light'])
    expect(l.earnedBadges.first_light).toBeTruthy()
    c.checkBadges()
    expect(c.newlyEarned).toHaveLength(1)
    l.light('b', 'gps'); c.checkBadges()
    expect(c.newlyEarned.map((b) => b.id)).toEqual(['first_light', 'jinju8'])
    expect(c.consumeNewlyEarned().map((b) => b.id)).toEqual(['first_light', 'jinju8'])
    expect(c.newlyEarned).toEqual([])
    c.checkBadges(); expect(c.newlyEarned).toEqual([])
  })
})
