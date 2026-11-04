import { afterEach, describe, expect, test } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DemoSettings from '../DemoSettings.vue'
import { useLanternsStore } from '../../../stores/lanterns'
import { closeDemoSettings, openDemoSettings } from '../../../composables/useDemoSettings'

afterEach(closeDemoSettings)

describe('DemoSettings', () => {
  test('preset sets lantern festival date and enables demo', async () => {
    openDemoSettings()
    const w = mount(DemoSettings)
    await w.find('[data-test="preset-festival"]').trigger('click')
    const s = useLanternsStore()
    expect(s.demo.today).toBe('2026-10-10')
    expect(s.demo.enabled).toBe(true)
    w.unmount()
  })

  test('toggle off disables demo', async () => {
    const s = useLanternsStore()
    s.setDemo({ enabled: true, today: '2026-10-10', pos: null })
    openDemoSettings()
    const w = mount(DemoSettings)
    await w.find('[data-test="demo-toggle"]').setValue(false)
    expect(s.demo.enabled).toBe(false)
    w.unmount()
  })

  test('today preset and date input', async () => {
    openDemoSettings()
    const w = mount(DemoSettings)
    await w.find('[data-test="demo-date"]').setValue('2026-10-05')
    expect(useLanternsStore().demo).toMatchObject({ enabled: true, today: '2026-10-05' })
    await w.find('[data-test="preset-today"]').trigger('click')
    expect(useLanternsStore().demo.today).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    w.unmount()
  })

  test('Esc closes', async () => {
    openDemoSettings()
    const w = mount(DemoSettings)
    await w.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    w.unmount()
  })
})
