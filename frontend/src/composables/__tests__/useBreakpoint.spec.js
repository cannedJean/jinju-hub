import { afterEach, describe, expect, it, vi } from 'vitest'
import { useBreakpoint } from '../useBreakpoint'

function mockWidth(width) {
  window.matchMedia = vi.fn().mockImplementation((query) => {
    const min = /min-width:\s*(\d+)px/.exec(query)
    const max = /max-width:\s*(\d+)px/.exec(query)
    const matches = (!min || width >= +min[1]) && (!max || width <= +max[1])
    return {
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }
  })
}

describe('useBreakpoint', () => {
  afterEach(() => {
    delete window.matchMedia
  })

  it.each([
    [390, [true, false, false]],
    [1024, [false, true, false]],
    [1440, [false, false, true]],
  ])('width %i -> mobile/tablet/desktop %j', (width, [m, t, d]) => {
    mockWidth(width)
    const { isMobile, isTablet, isDesktop } = useBreakpoint()
    expect([isMobile.value, isTablet.value, isDesktop.value]).toEqual([m, t, d])
  })
})
