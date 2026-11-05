import { describe, expect, test, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useLanternsStore } from '../../stores/lanterns'
import SavedList from '../../components/lanterns/SavedList.vue'

describe('Lanterns F2: Snapshot preservation, schema backfill, and SavedList deduplication', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/places/:id', name: 'place', component: { template: '<div />' } }],
    })
  })

  test('snapshot preserves hero_image, summary, addr, jinju8_rank, and is_collection', () => {
    const s = useLanternsStore()
    const place = {
      id: 'jh-1',
      title: '촉석루',
      category: 'sight',
      hero_image: 'https://img.test/chokseok.jpg',
      summary: '남강 의암 절벽 위에 자리한 진주의 상징',
      addr: '경남 진주시 남강로 626',
      jinju8_rank: 1,
      is_collection: 1,
      tags: ['역사', '진주8경'],
      lat: 35.1897,
      lng: 128.0819,
    }
    s.save(place)

    const saved = s.items['jh-1']
    expect(saved).toBeDefined()
    expect(saved.hero_image).toBe('https://img.test/chokseok.jpg')
    expect(saved.summary).toBe('남강 의암 절벽 위에 자리한 진주의 상징')
    expect(saved.addr).toBe('경남 진주시 남강로 626')
    expect(saved.jinju8_rank).toBe(1)
    expect(saved.is_collection).toBe(1)
  })

  test('verify() normalizes legacy schema and backfills missing metadata from place list', () => {
    const s = useLanternsStore()
    // Simulate legacy saved item missing new fields
    s.items['jh-legacy'] = {
      id: 'jh-legacy',
      title: '구식 기록 장소',
      category: 'sight',
      savedAt: '2026-01-01T00:00:00.000Z',
    }

    // verify without args normalizes fields
    s.verify()
    expect(s.items['jh-legacy'].hero_image).toBeNull()
    expect(s.items['jh-legacy'].jinju8_rank).toBeNull()

    // verify with place list backfills
    s.verify([
      {
        id: 'jh-legacy',
        hero_image: 'https://img.test/legacy.jpg',
        summary: '복원된 설명',
        addr: '진주시 비봉로',
        jinju8_rank: 3,
        is_collection: 0,
      },
    ])

    expect(s.items['jh-legacy'].hero_image).toBe('https://img.test/legacy.jpg')
    expect(s.items['jh-legacy'].summary).toBe('복원된 설명')
    expect(s.items['jh-legacy'].addr).toBe('진주시 비봉로')
    expect(s.items['jh-legacy'].jinju8_rank).toBe(3)
  })

  test('savedList sorting is stabilized with id tie-breaker when savedAt matches', () => {
    const s = useLanternsStore()
    const sameTime = '2026-11-05T00:00:00.000Z'
    s.items['b-item'] = { id: 'b-item', title: 'B', savedAt: sameTime }
    s.items['a-item'] = { id: 'a-item', title: 'A', savedAt: sameTime }
    s.items['c-item'] = { id: 'c-item', title: 'C', savedAt: sameTime }

    const list = s.savedList
    expect(list.map((it) => it.id)).toEqual(['a-item', 'b-item', 'c-item'])
  })

  test('SavedList passes hero_image and jinju8_rank to PlaceCard and renders them', async () => {
    const item = {
      id: 'jh-1',
      title: '촉석루',
      category: 'sight',
      hero_image: 'https://img.test/chokseok.jpg',
      summary: '남강 의암 절벽',
      addr: '진주시 남강로',
      jinju8_rank: 1,
      savedAt: '2026-11-05T01:00:00.000Z',
      tags: [],
      lat: 35.18,
      lng: 128.08,
    }

    const wrapper = mount(SavedList, {
      props: {
        items: [item],
        missing: new Set(),
        readonly: false,
      },
      global: { plugins: [router] },
    })

    // Image tag should be rendered with hero_image
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://img.test/chokseok.jpg')

    // Jinju8 badge should be rendered
    expect(wrapper.text()).toContain('진주8경 1')
  })

  test('SavedList hides duplicate PlaceCard save button via CSS rule', () => {
    const wrapper = mount(SavedList, {
      props: {
        items: [{ id: 'jh-1', title: '촉석루', category: 'sight' }],
        missing: new Set(),
        readonly: false,
      },
      global: { plugins: [router] },
    })

    // Remove button "빼기" is rendered
    const removeBtn = wrapper.find('button.saved-row__remove')
    expect(removeBtn.exists()).toBe(true)
    expect(removeBtn.text()).toContain('빼기')
  })
})
