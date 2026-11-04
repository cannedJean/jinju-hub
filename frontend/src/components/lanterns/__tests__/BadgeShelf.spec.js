import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import BadgeShelf from '../BadgeShelf.vue'

describe('BadgeShelf', () => {
  test('renders jinju8 progress 2/8 with progressbar semantics', () => {
    const w = mount(BadgeShelf, {
      props: { badges: [{ id: 'jinju8', label: '진주8경', description: '8경 점등', required: 8, progress: 2, earned: false }] },
    })
    const bar = w.find('[role="progressbar"]')
    expect(bar.attributes('aria-valuenow')).toBe('2')
    expect(bar.attributes('aria-valuemax')).toBe('8')
    expect(w.text()).toContain('2/8')
  })

  test('earned badge is marked lit', () => {
    const w = mount(BadgeShelf, {
      props: { badges: [{ id: 'first_light', label: '첫 유등', description: '', required: 1, progress: 1, earned: true }] },
    })
    expect(w.find('[data-earned="true"]').exists()).toBe(true)
    expect(w.text()).toContain('획득')
  })
})
