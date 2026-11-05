import { describe, expect, test, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppTabBar from '../../components/layout/AppTabBar.vue'
import ChatWidget from '../../components/ChatWidget.vue'

describe('Mobile Layer z-index Hierarchy F7', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/explore', component: { template: '<div />' } },
        { path: '/lanterns', component: { template: '<div />' } },
        { path: '/festivals', component: { template: '<div />' } },
        { path: '/boards', component: { template: '<div />' } },
        { path: '/about/data', component: { template: '<div />' } },
      ],
    })
  })

  test('AppTabBar more-sheet modal has z-[120] and backdrop has z-[110], properly overlaying ChatWidget', async () => {
    const w = mount(AppTabBar, { global: { plugins: [router] } })

    // Open more menu
    await w.find('[data-test="more-tab"]').trigger('click')
    await flushPromises()

    const backdrop = w.find('[data-test="more-backdrop"]')
    expect(backdrop.exists()).toBe(true)
    expect(backdrop.classes()).toContain('z-[110]')

    const sheet = w.find('#more-sheet')
    expect(sheet.exists()).toBe(true)
    expect(sheet.classes()).toContain('z-[120]')
  })

  test('ChatWidget has z-[100] so more-sheet at z-[120] overlays it cleanly', () => {
    const chat = mount(ChatWidget, { global: { plugins: [router] } })
    expect(chat.find('.fixed').classes()).toContain('z-[100]')
  })
})
