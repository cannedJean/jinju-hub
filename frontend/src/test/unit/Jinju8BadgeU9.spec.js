import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import HomeView from '../../views/HomeView.vue'
import BadgeShelf from '../../components/lanterns/BadgeShelf.vue'
import { useCollectionStore } from '../../stores/collection'

vi.mock('../../api/places', () => ({
  fetchFestivals: vi.fn(() => Promise.resolve({ items: [], today: '2026-11-04' })),
  fetchCollection: vi.fn(() => Promise.resolve({
    collection_ids: ['jh-1', 'jh-2'],
    jinju8: [
      { id: 'jh-1', rank: 1, title: '진주성 촉석루', hero_image: 'https://example.com/chokseoknu.jpg' },
      { id: 'jh-2', rank: 2, title: '남강 의암', hero_image: null },
    ],
    badges: [],
  })),
  fetchPlace: vi.fn((id) => Promise.resolve({
    id,
    hero_image: id === 'jh-2' ? 'https://example.com/uiam.jpg' : null,
  })),
  fetchMeta: vi.fn(() => Promise.resolve({})),
}))

vi.mock('../../api/weather', () => ({
  fetchWeather: vi.fn(() => Promise.resolve({})),
}))

const Stub = { template: '<div />' }
function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Stub },
      { path: '/places/:id', component: Stub },
      { path: '/explore', component: Stub },
      { path: '/festivals', component: Stub },
      { path: '/lanterns', component: Stub },
    ],
  })
}

describe('U9 - Jinju 8 Image Cards in HomeView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders image cards with genuine img tags and object-contain for Jinju 8 scenic spots', async () => {
    const router = makeRouter()
    const w = mount(HomeView, { global: { plugins: [router] } })
    await flushPromises()

    const cards = w.findAll('[data-test="jinju8-card"]')
    expect(cards.length).toBe(2)

    // First card has hero_image
    const firstImg = cards[0].find('img')
    expect(firstImg.exists()).toBe(true)
    expect(firstImg.attributes('src')).toBe('https://example.com/chokseoknu.jpg')
    expect(firstImg.classes()).toContain('object-contain')

    w.unmount()
  })

  test('shows fallback placeholder when image is missing or triggers error', async () => {
    const router = makeRouter()
    const w = mount(HomeView, { global: { plugins: [router] } })
    await flushPromises()

    const cards = w.findAll('[data-test="jinju8-card"]')
    const firstImg = cards[0].find('img')
    expect(firstImg.exists()).toBe(true)

    // Trigger image error
    await firstImg.trigger('error')

    // Expect fallback to be displayed instead of broken img
    expect(cards[0].find('img').exists()).toBe(false)
    expect(cards[0].find('[data-test="jinju8-fallback"]').exists()).toBe(true)

    w.unmount()
  })
})

describe('U9 - Distinct Badge Tier Glyphs in BadgeShelf', () => {
  test('renders distinct icons per badge id instead of uniform diamonds', () => {
    const badges = [
      { id: 'first_light', label: '첫 등불', description: '첫 유등 점등', required: 1, progress: 1, earned: true },
      { id: 'jinju8', label: '진주8경 탐험가', description: '진주8경 완주', required: 8, progress: 2, earned: false },
      { id: 'food_explorer', label: '맛 탐험가', description: '맛집 탐방', required: 5, progress: 5, earned: true },
      { id: 'history_walk', label: '역사 산책', description: '역사 명소', required: 3, progress: 0, earned: false },
      { id: 'night_namgang', label: '밤의 남강', description: '야간 관광', required: 4, progress: 4, earned: true },
      { id: 'festival_guest', label: '축제 손님', description: '축제 방문', required: 1, progress: 1, earned: true },
    ]

    const w = mount(BadgeShelf, { props: { badges } })
    const items = w.findAll('.badge')
    expect(items.length).toBe(6)

    const text = w.text()
    expect(text).toContain('🏮') // first_light
    expect(text).toContain('🏰') // jinju8
    expect(text).toContain('🥢') // food_explorer
    expect(text).toContain('📜') // history_walk
    expect(text).toContain('🌙') // night_namgang
    expect(text).toContain('🎆') // festival_guest

    // Uniform diamond ◆ or ◇ should NOT be used as the badge icon
    const icons = w.findAll('.badge__icon').map((el) => el.text())
    expect(icons).not.toContain('◆')
    expect(icons).not.toContain('◇')

    w.unmount()
  })
})
