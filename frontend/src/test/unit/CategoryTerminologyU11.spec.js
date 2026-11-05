import { describe, expect, test } from 'vitest'
import { categoryLabel, CATEGORY_LABELS } from '../../utils/format'
import { POST_CATEGORIES, getCategoryLabel } from '../../utils/constants'
import * as rootConstants from '../../constants'

describe('U11 - Harmonize Place Category Terminology (명소 vs 관광지)', () => {
  test('POST_CATEGORIES has unified label "명소" for tour category', () => {
    const tourCategory = POST_CATEGORIES.find((c) => c.id === 'tour')
    expect(tourCategory).toBeDefined()
    expect(tourCategory?.label).toBe('명소')
    expect(getCategoryLabel('tour')).toBe('명소')
  })

  test('categoryLabel maps both sight and tour to "명소"', () => {
    expect(categoryLabel('sight')).toBe('명소')
    expect(categoryLabel('tour')).toBe('명소')
    expect(CATEGORY_LABELS.sight).toBe('명소')
    expect(CATEGORY_LABELS.tour).toBe('명소')
  })

  test('frontend/src/constants.js re-exports aligned constants', () => {
    expect(rootConstants.POST_CATEGORIES).toBeDefined()
    const tourCat = rootConstants.POST_CATEGORIES.find((c) => c.id === 'tour')
    expect(tourCat?.label).toBe('명소')
    expect(rootConstants.getCategoryLabel('tour')).toBe('명소')
  })
})
