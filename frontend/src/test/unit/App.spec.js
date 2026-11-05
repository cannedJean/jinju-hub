import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import App from '../../App.vue'

vi.mock('../../api/places', () => ({
  fetchFestivals: vi.fn(() => Promise.resolve({ items: [], today: '2026-11-04' })),
  fetchCollection: vi.fn(() => Promise.resolve({ collection_ids: [], badges: [] })),
  fetchMeta: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../../api/weather', () => ({
  fetchWeather: vi.fn(() => Promise.resolve({})),
}))

function mockMatchMedia(width = 1024) {
  window.matchMedia = vi.fn().mockImplementation((query) => {
    const min = /min-width:\s*(\d+)px/.exec(query)
    const max = /max-width:\s*(\d+)px/.exec(query)
    const matches = (!min || width >= +min[1]) && (!max || width <= +max[1])
    return {
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }
  })
}

const Stub = { template: '<div />' }
const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/', component: Stub }],
})

describe('App.vue F5 - Skip Navigation Link and Main Content Target', () => {
  beforeEach(() => {
    mockMatchMedia()
  })

  afterEach(() => {
    delete window.matchMedia
  })

  test('renders skip navigation link pointing to #main-content', () => {
    setActivePinia(createPinia())
    const w = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          WakingBanner: true,
          DemoBanner: true,
          AppHeader: true,
          AppFooter: true,
          AppTabBar: true,
          ChatWidget: true,
          CelebrationToast: true,
          DemoSettings: true,
        },
      },
    })

    const skipLink = w.find('a[href="#main-content"]')
    expect(skipLink.exists()).toBe(true)
    expect(skipLink.text()).toBe('본문 바로가기')
    expect(skipLink.classes()).toContain('sr-only')
    expect(skipLink.classes()).toContain('focus:not-sr-only')
    expect(skipLink.classes()).toContain('focus:fixed')

    const main = w.find('main#main-content')
    expect(main.exists()).toBe(true)
    expect(main.attributes('tabindex')).toBe('-1')
    w.unmount()
  })
})
