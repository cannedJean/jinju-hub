import { describe, expect, test } from 'vitest'
import { decodeShare, encodeShare } from '../share'

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
  test('caps at 100', () => {
    const ids = Array.from({ length: 150 }, (_, i) => `jh-${i}`)
    expect(decodeShare(encodeShare(ids))).toHaveLength(100)
  })
  test('empty / non-string input', () => {
    expect(decodeShare('')).toEqual([])
    expect(decodeShare(null)).toEqual([])
    expect(decodeShare(undefined)).toEqual([])
    expect(encodeShare([])).toBe('')
  })
})
