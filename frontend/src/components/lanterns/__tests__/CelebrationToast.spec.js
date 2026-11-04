import { describe, expect, test } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CelebrationToast from '../CelebrationToast.vue'
import { useCollectionStore } from '../../../stores/collection'
import { useLanternsStore } from '../../../stores/lanterns'

describe('CelebrationToast', () => {
  test('first light shows toast', async () => {
    const w = mount(CelebrationToast)
    useLanternsStore().light('jh-a', 'gps', { id: 'jh-a', title: 'A' })
    await flushPromises()
    expect(w.text()).toContain('첫 유등을 밝혔어요!')
    w.unmount()
  })

  test('badge modal closes with button and Esc', async () => {
    const w = mount(CelebrationToast)
    const c = useCollectionStore()
    c.newlyEarned.push({ id: 'jinju8', label: '진주8경 탐험가', description: 'd' })
    await flushPromises()
    expect(w.text()).toContain('진주8경 탐험가')
    expect(c.newlyEarned).toHaveLength(0)
    await w.find('[role="dialog"] button').trigger('click')
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    c.newlyEarned.push({ id: 'x', label: '두번째', description: '' })
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(true)
    await w.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    w.unmount()
  })
})
