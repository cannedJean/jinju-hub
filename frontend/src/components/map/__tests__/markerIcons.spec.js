import { describe, expect, test } from 'vitest'
import { buildMarkerOptions, clusterSummary, makeClusterIcon, makeMarkerIcon, markerState } from '../markerIcons'

describe('makeMarkerIcon', () => {
  test('lit icon carries category, state and glow', () => {
    const icon = makeMarkerIcon({ category: 'food', state: 'lit' })
    expect(icon.options.className).toContain('marker--food')
    expect(icon.options.className).toContain('marker--lit')
    expect(icon.options.html).toContain('lantern-glow')
    expect(icon.options.html).toContain('lantern--filled')
  })

  test('saved icon is an outlined lantern without glow', () => {
    const icon = makeMarkerIcon({ category: 'sight', state: 'saved' })
    expect(icon.options.className).toContain('marker--saved')
    expect(icon.options.html).toContain('lantern--outline')
    expect(icon.options.html).not.toContain('lantern-glow')
  })

  test('plain pin, highlight and unknown category', () => {
    const plain = makeMarkerIcon({ category: 'stay', state: 'none' })
    expect(plain.options.className).toContain('marker--none')
    expect(plain.options.className).not.toContain('marker--active')
    expect(makeMarkerIcon({ category: 'stay', state: 'none', highlighted: true }).options.className).toContain(
      'marker--active',
    )
    const odd = makeMarkerIcon({ category: '"><img src=x>', state: 'weird' })
    expect(odd.options.className).toContain('marker--etc')
    expect(odd.options.className).toContain('marker--none')
    expect(odd.options.className).not.toContain('<')
  })
})

describe('markerState', () => {
  test('lit wins over saved', () => {
    expect(markerState('a', new Set(['a']), new Set(['a']))).toBe('lit')
    expect(markerState('a', new Set(['a']), new Set())).toBe('saved')
    expect(markerState('a', new Set(), new Set())).toBe('none')
    expect(markerState('a', undefined, undefined)).toBe('none')
  })
})

describe('buildMarkerOptions', () => {
  test('uses the place title for title/alt and enables keyboard', () => {
    expect(buildMarkerOptions({ id: 'jh-1', title: '촉석루', lat: 35.19, lng: 128.08, category: 'sight' })).toEqual({
      title: '촉석루',
      alt: '촉석루',
      keyboard: true,
    })
  })
})

describe('cluster icons', () => {
  test('summary picks the majority category and builds segments', () => {
    const s = clusterSummary(['food', 'food', 'sight', 'food'])
    expect(s.total).toBe(4)
    expect(s.majority).toBe('food')
    expect(s.segments.map((x) => x.category)).toEqual(['food', 'sight'])
    expect(s.segments[0]).toMatchObject({ from: 0, to: 75 })
    expect(s.segments[1]).toMatchObject({ from: 75, to: 100 })
  })

  test('cluster icon shows the count, majority class and an accessible label', () => {
    const icon = makeClusterIcon(['food', 'sight', 'food'])
    expect(icon.options.className).toContain('cluster--food')
    expect(icon.options.html).toContain('>3<')
    expect(icon.options.html).toContain('conic-gradient')
    expect(icon.options.html).toContain('장소 3곳')
  })
})
