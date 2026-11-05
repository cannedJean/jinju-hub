import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import Pagination from '../../components/Pagination.vue'
import CategoryChips from '../../components/explore/CategoryChips.vue'
import PlaceCard from '../../components/explore/PlaceCard.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/places/:id', name: 'place', component: { template: '<div />' } }],
})

describe('U4 - Touch Target Sizing >= 44px (WCAG 2.5.5)', () => {
  test('Pagination buttons meet minimum 44px touch target dimensions (min-h-[44px])', () => {
    const w = mount(Pagination, { props: { page: 1, totalPages: 5 } })
    const buttons = w.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
    for (const btn of buttons) {
      expect(btn.classes().some((c) => c.includes('min-h-[44px]'))).toBe(true)
      expect(btn.classes().some((c) => c.includes('min-w-[44px]'))).toBe(true)
    }
  })

  test('CategoryChips buttons meet minimum 44px touch target height (min-h-[44px])', () => {
    const w = mount(CategoryChips, {
      props: {
        categories: [],
        tags: [],
        counts: {},
        indoorRecommended: true,
      },
    })
    const chips = w.findAll('button.chip')
    expect(chips.length).toBeGreaterThan(0)
    for (const chip of chips) {
      expect(chip.classes().some((c) => c.includes('min-h-[44px]'))).toBe(true)
    }
  })

  test('PlaceCard interactive buttons meet minimum 44px touch target size (min-h-[44px])', () => {
    const place = {
      id: 'jh-stay1',
      title: '진주 게스트하우스',
      category: 'stay',
      lat: 35.18,
      lng: 128.08,
      summary: '숙소 설명',
    }
    const w = mount(PlaceCard, {
      props: { place, saved: false, lit: false },
      global: { plugins: [router] },
    })

    const saveBtn = w.find('button.place-card__save')
    expect(saveBtn.classes().some((c) => c.includes('min-h-[44px]'))).toBe(true)

    const mapBtn = w.find('button.place-card__map')
    expect(mapBtn.classes().some((c) => c.includes('min-h-[44px]'))).toBe(true)

    const actionBtn = w.find('button.place-card__action')
    expect(actionBtn.classes().some((c) => c.includes('min-h-[44px]'))).toBe(true)
  })
})
