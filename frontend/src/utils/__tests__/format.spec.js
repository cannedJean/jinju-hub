import { describe, expect, it } from 'vitest'
import { categoryLabel, formatDateRange, formatDistance } from '../format'

describe('formatDistance', () => {
  it('formats meters and kilometers', () => {
    expect(formatDistance(650)).toBe('650m')
    expect(formatDistance(1234)).toBe('1.2km')
  })
  it('returns empty string for null', () => {
    expect(formatDistance(null)).toBe('')
  })
})

describe('formatDateRange', () => {
  it('omits the year within the same year', () => {
    expect(formatDateRange('2026-10-03', '2026-10-18')).toBe('10.3 ~ 10.18')
  })
  it('includes years when they differ', () => {
    expect(formatDateRange('2026-12-31', '2027-01-02')).toBe('2026.12.31 ~ 2027.1.2')
  })
})

describe('categoryLabel', () => {
  it('maps codes to Korean labels', () => {
    expect(categoryLabel('culture')).toBe('문화·역사')
  })
})
