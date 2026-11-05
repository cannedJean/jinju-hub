import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/weather', () => ({ fetchWeather: vi.fn() }))
vi.mock('../../api/client', async (orig) => {
  const m = await orig()
  return { ...m, default: { get: vi.fn().mockResolvedValue({ data: {} }) } }
})

import WeatherWidget from '../WeatherWidget.vue'
import FestivalCard from '../festival/FestivalCard.vue'
import { fetchWeather } from '../../api/weather'
import apiClient from '../../api/client'
import { fetchPost } from '../../api/posts'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/', component: { template: '<div/>' } }, { path: '/explore', name: 'explore', component: { template: '<div/>' } }, { path: '/about/data', component: { template: '<div/>' } }],
})

describe('WeatherWidget', () => {
  beforeEach(() => vi.clearAllMocks())
  test('indoor recommendation shows link to explore?tags=indoor', async () => {
    fetchWeather.mockResolvedValue({ recommendation: 'indoor', temperature: 20, sky: 'rain' })
    const w = mount(WeatherWidget, { global: { plugins: [router] } })
    await flushPromises()
    expect(w.find('[data-test="indoor-link"]').attributes('href')).toBe('/explore?tags=indoor')
  })
  test('outdoor recommendation has no indoor link', async () => {
    fetchWeather.mockResolvedValue({ recommendation: 'outdoor', temperature: 20 })
    const w = mount(WeatherWidget, { global: { plugins: [router] } })
    await flushPromises()
    expect(w.find('[data-test="indoor-link"]').exists()).toBe(false)
  })
  test.each([
    ['clear', '☀️'],
    ['rain-snow', '🌨️'],
    ['01', '🌥️'], // OpenWeather-style codes are not emitted by the backend -> unknown icon
    ['', '🌥️'],
  ])('icon_code %j -> %s', async (code, icon) => {
    fetchWeather.mockResolvedValue({ recommendation: 'outdoor', temperature: 20, icon_code: code })
    const w = mount(WeatherWidget, { global: { plugins: [router] } })
    await flushPromises()
    expect(w.find('[data-test="weather-icon"]').text()).toBe(icon)
  })
})

describe('AppFooter', () => {
  test('map attribution names OpenStreetMap only (tiles are OSM)', async () => {
    const { setActivePinia, createPinia } = await import('pinia')
    setActivePinia(createPinia())
    const { default: AppFooter } = await import('../layout/AppFooter.vue')
    const w = mount(AppFooter, { global: { plugins: [router] } })
    expect(w.text()).toContain('지도 © OpenStreetMap contributors')
    expect(w.text()).not.toContain('CARTO')
  })
})

describe('FestivalCard', () => {
  test('image caption shown only with hero image', () => {
    const base = { id: 'f', title: 'T', start_date: '2026-10-01', end_date: '2026-10-05', status: 'ongoing' }
    const withImg = mount(FestivalCard, { props: { festival: { ...base, hero_image: 'http://x/y.jpg' } }, global: { plugins: [router] } })
    expect(withImg.text()).toContain('사진: 한국관광공사·진주시 제공')
    const without = mount(FestivalCard, { props: { festival: base }, global: { plugins: [router] } })
    expect(without.text()).not.toContain('사진:')
  })
})

describe('fetchPost', () => {
  test('countView=false sends count_view=false; default sends no params', async () => {
    await fetchPost(1, { countView: false })
    expect(apiClient.get).toHaveBeenLastCalledWith('/posts/1', { params: { count_view: false } })
    await fetchPost(2)
    expect(apiClient.get).toHaveBeenLastCalledWith('/posts/2', undefined)
  })
})
