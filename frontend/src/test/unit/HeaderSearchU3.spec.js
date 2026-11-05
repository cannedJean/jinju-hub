import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import AppHeader from '../../components/layout/AppHeader.vue'

vi.mock('../../api/weather', () => ({
  fetchWeather: vi.fn(() => Promise.resolve({ temperature: 18, condition: '맑음' })),
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

describe('U3 - Mobile Header Search Bar Integration', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: Stub },
        { path: '/explore', name: 'explore', component: Stub },
        { path: '/lanterns', name: 'lanterns', component: Stub },
        { path: '/festivals', name: 'festivals', component: Stub },
        { path: '/boards', name: 'boards', component: Stub },
        { path: '/about/data', name: 'data', component: Stub },
      ],
    })
  })

  afterEach(() => {
    delete window.matchMedia
  })

  test('search form and input are rendered on mobile viewports (390px)', () => {
    mockMatchMedia(390)
    const w = mount(AppHeader, {
      global: {
        plugins: [router],
        stubs: { WeatherWidget: true },
      },
    })

    const form = w.find('form[role="search"]')
    expect(form.exists()).toBe(true)

    const input = w.find('input#header-search')
    expect(input.exists()).toBe(true)
    expect(input.attributes('placeholder')).toContain('검색')
    w.unmount()
  })

  test('mobile search submission navigates to explore with search query', async () => {
    mockMatchMedia(390)
    const w = mount(AppHeader, {
      global: {
        plugins: [router],
        stubs: { WeatherWidget: true },
      },
    })

    const input = w.find('input#header-search')
    await input.setValue('촉석루')

    const form = w.find('form[role="search"]')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('explore')
    expect(router.currentRoute.value.query.q).toBe('촉석루')
    w.unmount()
  })
})
