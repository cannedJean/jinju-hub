import { describe, expect, test } from 'vitest'
import { SHARE_MAX_IDS, capShareIds, decodeShare, encodeShare } from '../share'

describe('share', () => {
  test('roundtrip and junk', () => {
    expect(decodeShare(encodeShare(['jh-1', 'jh-2']))).toEqual(['jh-1', 'jh-2'])
    expect(decodeShare('%%%')).toEqual([])
  })
  test('url-safe, no padding', () => {
    const s = encodeShare(['jh-abc', 'jh-def', 'jh-???>>>'])
    expect(s).toMatch(/^[A-Za-z0-9_-]*$/)
  })
  test('drops non jh- entries', () => {
    expect(decodeShare(encodeShare(['jh-1', 'evil', '<script>']))).toEqual(['jh-1'])
  })
  test('dedupes, validates id charset, caps input length', () => {
    expect(decodeShare(encodeShare(['jh-1', 'jh-1', 'jh-a b', 'jh-cur-3']))).toEqual(['jh-1', 'jh-cur-3'])
    expect(decodeShare('A'.repeat(5000))).toEqual([])
  })
  test('caps at 100', () => {
    const ids = Array.from({ length: 150 }, (_, i) => `jh-${i}`)
    expect(decodeShare(encodeShare(ids))).toHaveLength(100)
  })
  test('encoder caps at the decoder limit and never produces a link the decoder rejects', () => {
    const ids = Array.from({ length: 300 }, (_, i) => `jh-${String(i).padStart(10, '0')}`)
    const s = encodeShare(ids)
    expect(s.length).toBeLessThanOrEqual(4096)
    expect(decodeShare(s)).toEqual(ids.slice(0, SHARE_MAX_IDS))
    expect(capShareIds(ids)).toHaveLength(100)
    expect(capShareIds(['jh-1'])).toEqual(['jh-1'])
  })
  test('empty / non-string input', () => {
    expect(decodeShare('')).toEqual([])
    expect(decodeShare(null)).toEqual([])
    expect(decodeShare(undefined)).toEqual([])
    expect(encodeShare([])).toBe('')
  })
})
