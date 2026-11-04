import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import BottomSheet, { SNAP_HEIGHTS } from '../BottomSheet.vue'

const handle = (w) => w.get('[data-test="sheet-handle"]')
const sheet = (w) => w.get('[data-test="sheet"]')

describe('BottomSheet', () => {
  test('snap heights match the spec', () => {
    expect(SNAP_HEIGHTS).toEqual({ collapsed: '96px', half: '50vh', full: '90vh' })
  })

  test('handle click cycles collapsed -> half -> full -> collapsed and updates aria-expanded', async () => {
    const w = mount(BottomSheet, { slots: { default: '<p>목록</p>' } })
    expect(sheet(w).attributes('data-snap')).toBe('collapsed')
    expect(handle(w).attributes('aria-expanded')).toBe('false')
    expect(sheet(w).attributes('style')).toContain('96px')

    await handle(w).trigger('click')
    expect(sheet(w).attributes('data-snap')).toBe('half')
    expect(handle(w).attributes('aria-expanded')).toBe('true')
    expect(sheet(w).attributes('style')).toContain('50vh')

    await handle(w).trigger('click')
    expect(sheet(w).attributes('data-snap')).toBe('full')
    expect(sheet(w).attributes('style')).toContain('90vh')

    await handle(w).trigger('click')
    expect(sheet(w).attributes('data-snap')).toBe('collapsed')
    expect(handle(w).attributes('aria-expanded')).toBe('false')
  })

  test('works as v-model:snap and emits updates', async () => {
    const w = mount(BottomSheet, { props: { snap: 'half' } })
    await handle(w).trigger('click')
    expect(w.emitted('update:snap')[0]).toEqual(['full'])
  })

  test('arrow keys step between snaps', async () => {
    const w = mount(BottomSheet)
    await handle(w).trigger('keydown', { key: 'ArrowUp' })
    expect(sheet(w).attributes('data-snap')).toBe('half')
    await handle(w).trigger('keydown', { key: 'ArrowUp' })
    await handle(w).trigger('keydown', { key: 'ArrowUp' })
    expect(sheet(w).attributes('data-snap')).toBe('full')
    await handle(w).trigger('keydown', { key: 'ArrowDown' })
    expect(sheet(w).attributes('data-snap')).toBe('half')
  })
})
