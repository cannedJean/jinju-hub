import { describe, expect, test } from 'vitest'
import { toSourceLinks } from '../chatSources'

describe('toSourceLinks', () => {
  test('maps place/post and ignores unknown types', () => {
    const links = toSourceLinks([
      { type: 'place', id: 'jh-1', label: '촉석루' },
      { type: 'post', id: '3', label: '후기' },
      { type: 'location', id: 'x', label: '?' },
    ])
    expect(links).toHaveLength(2)
    expect(links[0]).toEqual({ to: { name: 'place', params: { id: 'jh-1' } }, label: '촉석루', kind: 'place', placeId: 'jh-1' })
    expect(links[1].to).toEqual({ name: 'post', params: { id: '3' } })
    expect(links[1].kind).toBe('post')
  })
  test('tolerates non-arrays and null entries', () => {
    expect(toSourceLinks(undefined)).toEqual([])
    expect(toSourceLinks([null, { type: 'place' }])).toEqual([])
  })
})
