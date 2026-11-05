import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import FestivalTimeline from '../../components/festival/FestivalTimeline.vue'

describe('U7 - Festival Timeline Mobile View', () => {
  const FESTIVALS = [
    {
      id: 'f-yudeung',
      title: '진주남강유등축제',
      status: 'ongoing',
      start_date: '2026-10-01',
      end_date: '2026-10-15',
    },
    {
      id: 'f-gaechon',
      title: '개천예술제',
      status: 'upcoming',
      start_date: '2026-10-03',
      end_date: '2026-10-10',
    },
  ]

  test('timeline has overflow-x-auto wrapper and min-w-[640px] container for mobile responsiveness', () => {
    const wrapper = mount(FestivalTimeline, {
      props: { festivals: FESTIVALS, today: '2026-10-05' },
    })

    const scrollWrapper = wrapper.find('.overflow-x-auto')
    expect(scrollWrapper.exists()).toBe(true)

    const minWidthContainer = scrollWrapper.find('.min-w-\\[640px\\]')
    expect(minWidthContainer.exists()).toBe(true)
  })

  test('timeline bars prevent extreme truncation with min-width of at least 3.5rem', () => {
    const wrapper = mount(FestivalTimeline, {
      props: { festivals: FESTIVALS, today: '2026-10-05' },
    })

    const bar = wrapper.find('[data-test="timeline-bar"] span')
    expect(bar.exists()).toBe(true)
    const style = bar.attributes('style') || ''
    expect(style).toMatch(/min-width:\s*(3\.[5-9]rem|[4-9]rem)/)
  })
})
