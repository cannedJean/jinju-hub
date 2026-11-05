import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import AppHeader from '../../components/layout/AppHeader.vue'
import ExploreView from '../../views/ExploreView.vue'

vi.mock('../../api/places', () => ({
  fetchPlaces: vi.fn(() => Promise.resolve({ items: [], total: 0 })),
  fetchMarkers: vi.fn(() => Promise.resolve({ items: [] })),
  fetchFestivals: vi.fn(() => Promise.resolve({ items: [] })),
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
  routes: [
    { path: '/', component: Stub },
    { path: '/explore', name: 'explore', component: Stub },
    { path: '/lanterns', component: Stub },
    { path: '/festivals', component: Stub },
    { path: '/boards', component: Stub },
    { path: '/about/data', component: Stub },
  ],
})

describe('U8 - Form Input Accessibility & Pretendard font', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    delete window.matchMedia
  })

  test('AppHeader search input has explicit id, name="search", and matching label/aria-label', () => {
    mockMatchMedia(1440) // Desktop so search input is rendered
    const w = mount(AppHeader, {
      global: {
        plugins: [router],
        stubs: {
          WeatherWidget: true,
        },
      },
    })

    const input = w.find('input[type="search"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('id')).toBe('header-search')
    expect(input.attributes('name')).toBe('search')
    expect(input.attributes('aria-label')).toBe('장소 검색')

    const label = w.find('label[for="header-search"]')
    expect(label.exists()).toBe(true)
    expect(label.text()).toContain('장소 검색')
    w.unmount()
  })

  test('ExploreView mobile sheet search input has explicit id, name="search", and matching label/aria-label', () => {
    mockMatchMedia(390) // Mobile so bottom sheet search input is rendered
    const w = mount(ExploreView, {
      global: {
        plugins: [router],
        stubs: {
          MapCanvas: true,
          BasePointControl: true,
          PlaceCard: true,
          Pagination: true,
          CategoryChips: true,
        },
      },
    })

    const input = w.find('input[type="search"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('id')).toBe('sheet-search')
    expect(input.attributes('name')).toBe('search')
    expect(input.attributes('aria-label')).toBe('장소 검색')

    const label = w.find('label[for="sheet-search"]')
    expect(label.exists()).toBe(true)
    expect(label.text()).toContain('장소 검색')
    w.unmount()
  })

  test('index.html loads Pretendard web font', () => {
    const htmlPath = resolve(__dirname, '../../../index.html')
    const html = readFileSync(htmlPath, 'utf-8')
    expect(html).toContain('pretendard')
  })
})
