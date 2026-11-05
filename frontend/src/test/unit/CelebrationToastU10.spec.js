import { beforeEach, describe, expect, test } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CelebrationToast from '../../components/lanterns/CelebrationToast.vue'
import { useCollectionStore } from '../../stores/collection'
import { useLanternsStore } from '../../stores/lanterns'

describe('U10 - Celebration Toast Wording Polish & Modal Suppression', () => {
  beforeEach(() => {
    localStorage.clear()
    const l = useLanternsStore()
    l.$reset()
  })

  test('toast clearly mentions lantern lit and badge added to storage', async () => {
    const w = mount(CelebrationToast)
    const l = useLanternsStore()

    // Light the very first lantern
    l.light('jh-a', 'gps', { id: 'jh-a', title: '진주성' })
    await flushPromises()

    const text = w.text()
    // Must clearly announce milestone and badge added to storage
    expect(text).toContain('배지가 보관함에 추가되었어요')
    expect(text).toContain('첫 유등을 밝혔어요!')

    // STRICT Section 4-3 DO NOT rule: Modal dialog MUST NOT appear for first light
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    w.unmount()
  })

  test('regular milestone badges still open modal while first_light is excluded', async () => {
    const w = mount(CelebrationToast)
    const c = useCollectionStore()

    // Enqueue first_light and jinju8
    c.newlyEarned.push({ id: 'first_light', label: '첫 등불' })
    c.newlyEarned.push({ id: 'jinju8', label: '진주8경 탐험가', description: '진주8경 완주' })
    await flushPromises()

    // Modal opens for jinju8, not first_light
    expect(w.find('[role="dialog"]').exists()).toBe(true)
    expect(w.find('#badge-title').text()).toBe('진주8경 탐험가')

    w.unmount()
  })
})
