import { describe, expect, it } from 'vitest'
import router from '../index'

describe('router', () => {
  const cases = [
    ['/', 'home'],
    ['/explore', 'explore'],
    ['/places/jh-1', 'place'],
    ['/lanterns', 'lanterns'],
    ['/festivals', 'festivals'],
    ['/boards', 'boards'],
    ['/boards/new', 'post-new'],
    ['/boards/12', 'post'],
    ['/boards/12/edit', 'post-edit'],
    ['/about/data', 'data'],
    ['/nope/missing', 'not-found'],
  ]
  it.each(cases)('resolves %s to %s', (path, name) => {
    expect(router.resolve(path).name).toBe(name)
  })

  it('passes place id param', () => {
    expect(router.resolve('/places/jh-1').params.id).toBe('jh-1')
  })
})
