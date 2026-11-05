import { describe, expect, test, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppTabBar from '../../components/layout/AppTabBar.vue'

describe('U1 - Mobile Tab Bar Home Tab', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/explore', component: { template: '<div>Explore</div>' } },
        { path: '/lanterns', component: { template: '<div>Lanterns</div>' } },
        { path: '/festivals', component: { template: '<div>Festivals</div>' } },
        { path: '/boards', component: { template: '<div>Boards</div>' } },
        { path: '/about/data', component: { template: '<div>Data</div>' } },
      ],
    })
  })

  test('AppTabBar includes Home tab linking to / as first item in navigation', () => {
    const w = mount(AppTabBar, { global: { plugins: [router] } })
    const links = w.findAll('nav[aria-label="하단 메뉴"] a')

    // Should have 4 links: 홈, 탐색, 내 유등, 축제
    expect(links).toHaveLength(4)

    const homeLink = links[0]
    expect(homeLink.attributes('href')).toBe('/')
    expect(homeLink.text()).toContain('홈')
  })

  test('Home tab renders home icon and correct label', () => {
    const w = mount(AppTabBar, { global: { plugins: [router] } })
    const homeLink = w.find('nav[aria-label="하단 메뉴"] a[href="/"]')

    expect(homeLink.exists()).toBe(true)
    expect(homeLink.text()).toContain('홈')
    expect(homeLink.find('span[aria-hidden="true"]').text()).toBe('🏠')
  })
})
