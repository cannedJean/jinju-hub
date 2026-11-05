import { describe, expect, test, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import WeatherWidget from '../../components/WeatherWidget.vue'
import { fetchWeather } from '../../api/weather'
import apiClient from '../../api/client'

vi.mock('../../api/weather', async (orig) => {
  const actual = await orig()
  return {
    ...actual,
    fetchWeather: vi.fn(),
  }
})

describe('Weather Widget & In-Flight Dedup F6', () => {
  let router

  beforeEach(() => {
    vi.clearAllMocks()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
  })

  test('non-compact WeatherWidget renders city and recommendation without hiding on mobile', async () => {
    fetchWeather.mockResolvedValueOnce({
      temperature: 19,
      condition: '맑음',
      recommendation: 'mixed',
      icon_code: 'clear',
    })

    const w = mount(WeatherWidget, {
      props: { compact: false },
      global: { plugins: [router] },
    })
    await flushPromises()

    // Entire text should include '진주 19°C' and '· 실내외 모두 좋음'
    expect(w.text()).toContain('진주 19°C')
    expect(w.text()).toContain('실내외 모두 좋음')

    // Find the recommendation span; it should NOT contain 'hidden md:inline' or 'hidden lg:inline'
    const spans = w.findAll('span')
    const recSpan = spans.find((s) => s.text().includes('실내외 모두 좋음'))
    expect(recSpan).toBeDefined()
    expect(recSpan.classes()).not.toContain('hidden')
  })

  test('compact WeatherWidget uses responsive hiding for header usage', async () => {
    fetchWeather.mockResolvedValueOnce({
      temperature: 19,
      condition: '맑음',
      recommendation: 'outdoor',
      icon_code: 'clear',
    })

    const w = mount(WeatherWidget, {
      props: { compact: true },
      global: { plugins: [router] },
    })
    await flushPromises()

    const spans = w.findAll('span')
    const recSpan = spans.find((s) => s.text().includes('야외활동 추천'))
    expect(recSpan).toBeDefined()
    expect(recSpan.classes()).toContain('hidden')
  })
})
