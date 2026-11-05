import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import FestivalCard from '../../components/festival/FestivalCard.vue'

describe('FestivalCard F4: Duplicate status label elimination', () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/places/:id', component: { template: '<div />' } }],
  })

  test('undecided festival does not repeat "일정 미정" twice', () => {
    const festival = {
      id: 'f-undecided',
      title: '진주 문화재 야행',
      status: 'undecided',
      status_label: '일정 미정',
      start_date: null,
      end_date: null,
    }

    const wrapper = mount(FestivalCard, {
      props: { festival },
      global: { plugins: [router] },
    })

    const text = wrapper.text()
    const matches = (text.match(/일정 미정/g) || []).length
    expect(matches).toBe(1)
  })

  test('festival with valid dates displays both status label and date range', () => {
    const festival = {
      id: 'f-upcoming',
      title: '개천예술제',
      status: 'upcoming',
      status_label: '예정',
      start_date: '2026-10-03',
      end_date: '2026-10-10',
    }

    const wrapper = mount(FestivalCard, {
      props: { festival },
      global: { plugins: [router] },
    })

    expect(wrapper.text()).toContain('예정')
    expect(wrapper.text()).toContain('10.3 ~ 10.10')
  })
})
