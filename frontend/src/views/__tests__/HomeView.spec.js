import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import HomeView from '../HomeView.vue'

vi.mock('../../api/places', () => ({
  fetchFestivals: vi.fn(() => Promise.resolve({ items: [], today: '2026-11-04' })),
  fetchCollection: vi.fn(() => Promise.resolve({ collection_ids: [], badges: [] })),
  fetchMeta: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../../api/weather', () => ({
  fetchWeather: vi.fn(() => Promise.resolve({})),
}))

const Stub = { template: '<div />' }
function plugins() {
  return [
    createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: Stub },
        { path: '/explore', component: Stub },
        { path: '/festivals', component: Stub },
        { path: '/lanterns', component: Stub },
        { path: '/:p(.*)*', component: Stub },
      ],
    }),
  ]
}

describe('HomeView R1 - Competition Theme Alignment', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('hero section renders aligned competition H1 title', async () => {
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    const h1 = w.find('h1')
    expect(h1.exists()).toBe(true)
    expect(h1.text()).toBe('빅데이터와 AI로 밝히는 진주의 밤 · 머무르고 싶은 여행')
    w.unmount()
  })

  test('hero section renders aligned competition subtitle', async () => {
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    const p = w.find('section p')
    expect(p.exists()).toBe(true)
    expect(p.text()).toBe(
      '1,250개 공공 데이터와 실시간 분석으로 혼잡은 피하고, 숨은 명소는 더 깊게. 낮의 촉석루부터 밤의 유등까지 나만의 체류형 여정을 완성하세요.',
    )
    w.unmount()
  })

  test('hero section renders 4 value proposition chips', async () => {
    const w = mount(HomeView, { global: { plugins: plugins() } })
    await flushPromises()
    const chips = w.findAll('[data-test="value-prop-chip"]')
    expect(chips.length).toBe(4)
    const texts = chips.map((c) => c.text())
    expect(texts).toContain('📊 1,250+ 공공 빅데이터')
    expect(texts).toContain('🌙 대한민국 1호 야간관광 특화도시')
    expect(texts).toContain('🤖 Claude AI 스마트 여행 비서')
    expect(texts).toContain('🏮 유등 게이미피케이션 동선 유도')
    w.unmount()
  })
})

describe('index.html R1 & U8 - Metadata and Web Fonts', () => {
  const htmlPath = resolve(__dirname, '../../../index.html')
  const html = readFileSync(htmlPath, 'utf-8')

  test('document title is updated to competition alignment', () => {
    expect(html).toContain('<title>JinjuHub | 빅데이터와 AI로 만나는 진주 관광</title>')
  })

  test('meta description is updated to competition alignment', () => {
    expect(html).toContain(
      'content="진주시 1,250개 공공 데이터와 AI가 추천하는 맞춤형 야간관광 및 체류형 여행. 낮의 촉석루부터 밤의 유등까지 스마트한 진주 여행을 시작하세요."',
    )
  })

  test('theme-color is #0f1b3d', () => {
    expect(html).toContain('<meta name="theme-color" content="#0f1b3d"')
  })

  test('OpenGraph tags are present', () => {
    expect(html).toContain('<meta property="og:title"')
    expect(html).toContain('<meta property="og:description"')
    expect(html).toContain('<meta property="og:image"')
    expect(html).toContain('<meta property="og:url"')
    expect(html).toContain('<meta property="og:site_name"')
    expect(html).toContain('<meta property="og:locale"')
  })

  test('Twitter card tags are present', () => {
    expect(html).toContain('<meta name="twitter:card"')
    expect(html).toContain('<meta name="twitter:title"')
    expect(html).toContain('<meta name="twitter:description"')
  })

  test('Pretendard webfont stylesheet link is present (U8)', () => {
    expect(html).toContain('pretendard')
  })
})
