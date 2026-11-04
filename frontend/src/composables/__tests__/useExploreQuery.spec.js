import { describe, expect, test } from 'vitest'
import { DEFAULT_STATE, parseQuery, patchState, searchState, toApiParams, toQuery } from '../useExploreQuery'

describe('parseQuery', () => {
  test('parses categories, near, radius and sort', () => {
    expect(parseQuery({ cat: 'food,sight', near: '35.19,128.08', radius: '1000', sort: 'distance' })).toEqual({
      q: '',
      categories: ['food', 'sight'],
      tags: [],
      bbox: null,
      near: { lat: 35.19, lng: 128.08 },
      radius: 1000,
      sort: 'distance',
      page: 1,
    })
  })

  test('empty query gives defaults', () => {
    expect(parseQuery({})).toEqual(DEFAULT_STATE)
    expect(parseQuery(undefined)).toEqual(DEFAULT_STATE)
  })

  test('invalid values fall back to defaults', () => {
    const s = parseQuery({
      near: 'abc',
      cat: 'food,bogus,food',
      tags: 'indoor,<script>',
      radius: '-5',
      sort: 'random',
      page: '0',
      bbox: '1,2,3',
    })
    expect(s.near).toBeNull()
    expect(s.categories).toEqual(['food'])
    expect(s.tags).toEqual(['indoor'])
    expect(s.radius).toBeNull()
    expect(s.sort).toBe('relevance')
    expect(s.page).toBe(1)
    expect(s.bbox).toBeNull()
  })

  test('rejects out-of-range near, unsupported radius and inverted bbox', () => {
    expect(parseQuery({ near: '95,128' }).near).toBeNull()
    expect(parseQuery({ near: '35.1,128.1,9' }).near).toBeNull()
    expect(parseQuery({ radius: '2000' }).radius).toBeNull()
    expect(parseQuery({ bbox: '128.2,35.1,128.1,35.2' }).bbox).toBeNull()
  })

  test('accepts a valid bbox, trims q, parses page, tolerates repeated keys', () => {
    const s = parseQuery({ bbox: '128.05,35.15,128.12,35.21', q: '  냉면 ', page: '3', cat: ['food', 'stay'] })
    expect(s.bbox).toBe('128.05,35.15,128.12,35.21')
    expect(s.q).toBe('냉면')
    expect(s.page).toBe(3)
    expect(s.categories).toEqual(['food', 'stay'])
  })
})

describe('toQuery', () => {
  test('omits defaults', () => {
    expect(toQuery(DEFAULT_STATE)).toEqual({})
    expect(toQuery(parseQuery({}))).toEqual({})
  })

  test('round-trips a full state', () => {
    const query = {
      q: '냉면',
      cat: 'food,sight',
      tags: 'indoor',
      bbox: '128.05,35.15,128.12,35.21',
      near: '35.19,128.08',
      radius: '1000',
      sort: 'distance',
      page: '2',
    }
    expect(toQuery(parseQuery(query))).toEqual(query)
  })
})

describe('toApiParams', () => {
  test('maps categories to repeated category keys and near to a string', () => {
    const params = toApiParams(parseQuery({ cat: 'food,sight', near: '35.19,128.08', radius: '1000', sort: 'distance' }))
    expect(params).toEqual({
      category: ['food', 'sight'],
      near: '35.19,128.08',
      radius: 1000,
      sort: 'distance',
      page: 1,
      size: 20,
    })
  })

  test('default state sends only paging and sort; no keyword ranks the collection first', () => {
    expect(toApiParams(DEFAULT_STATE)).toEqual({ sort: 'collection', page: 1, size: 20 })
    expect(toApiParams(parseQuery({ q: '냉면' }))).toEqual({ q: '냉면', sort: 'relevance', page: 1, size: 20 })
  })

  test('passes q, tags and bbox through', () => {
    const params = toApiParams(parseQuery({ q: '냉면', tags: 'indoor', bbox: '128.05,35.15,128.12,35.21' }))
    expect(params).toMatchObject({ q: '냉면', tags: ['indoor'], bbox: '128.05,35.15,128.12,35.21' })
  })

  test('radius without near is dropped; distance sort without any point becomes relevance', () => {
    expect(toApiParams(parseQuery({ q: '탕', radius: '1000', sort: 'distance' }))).toEqual({
      q: '탕',
      sort: 'relevance',
      page: 1,
      size: 20,
    })
  })

  test('fallback point adds distances without filtering', () => {
    const params = toApiParams(parseQuery({ sort: 'distance', radius: '500' }), {
      fallbackNear: { lat: 35.2, lng: 128.1 },
    })
    expect(params).toEqual({ near: '35.2,128.1', sort: 'distance', page: 1, size: 20 })
  })
})

describe('patchState', () => {
  test('resets page unless the patch sets it', () => {
    const s = parseQuery({ cat: 'food', page: '4' })
    expect(patchState(s, { categories: ['sight'] })).toMatchObject({ categories: ['sight'], page: 1 })
    expect(patchState(s, { page: 5 })).toMatchObject({ categories: ['food'], page: 5 })
  })
})

describe('searchState', () => {
  test('new keyword drops filters and bbox but keeps the lodging context', () => {
    const s = parseQuery({ cat: 'stay', tags: 'indoor', bbox: '128.05,35.15,128.12,35.21', near: '35.19,128.08', radius: '1000', sort: 'distance', page: '3' })
    expect(toQuery(searchState(s, ' 냉면 '))).toEqual({ q: '냉면', near: '35.19,128.08', radius: '1000', sort: 'distance' })
  })
})
