import { describe, expect, test, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import FestivalCard from '../../components/festival/FestivalCard.vue'
import { useMarkersStore } from '../../stores/markers'

describe('U5 - Festival Linked Place Name Dynamic Binding', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/places/:id', name: 'place', component: { template: '<div />' } }],
    })
  })

  test('displays festival.place_title when available on festival object', () => {
    const festival = {
      id: 'f-1',
      title: '진주남강유등축제',
      status: 'ongoing',
      status_label: '진행 중',
      venue_place_ids: ['jh-jinju-castle'],
      place_title: '진주성',
    }

    const wrapper = mount(FestivalCard, {
      props: { festival },
      global: { plugins: [router] },
    })

    const link = wrapper.find('a[href="/places/jh-jinju-castle"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('진주성')
    expect(wrapper.text()).not.toContain('행사 장소')
  })

  test('displays dynamic place title from markers store byId', () => {
    const markers = useMarkersStore()
    markers.items = [{ id: 'jh-chokseok', title: '진주 촉석루', category: 'sight' }]
    markers.loaded = true

    const festival = {
      id: 'f-2',
      title: '개천예술제',
      status: 'upcoming',
      status_label: '예정',
      venue_place_ids: ['jh-chokseok'],
    }

    const wrapper = mount(FestivalCard, {
      props: { festival },
      global: { plugins: [router] },
    })

    const link = wrapper.find('a[href="/places/jh-chokseok"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('진주 촉석루')
    expect(wrapper.text()).not.toContain('행사 장소')
  })

  test('falls back to festival.location when place_title is missing', () => {
    const festival = {
      id: 'f-3',
      title: '진주 논개제',
      status: 'ended',
      status_label: '종료',
      venue_place_ids: ['jh-unknown-venue'],
      location: '진주시 남강 둔치 일원',
    }

    const wrapper = mount(FestivalCard, {
      props: { festival },
      global: { plugins: [router] },
    })

    const link = wrapper.find('a[href="/places/jh-unknown-venue"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('진주시 남강 둔치 일원')
  })
})
