import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/places', () => ({ fetchPlace: vi.fn() }))
vi.mock('../../api/chat', () => ({ postChat: vi.fn() }))

import ChatWidget from '../ChatWidget.vue'
import { CHAT_SUGGESTIONS } from '../../data/chatSuggestions'
import { fetchPlace } from '../../api/places'
import { postChat } from '../../api/chat'
import { useLanternsStore } from '../../stores/lanterns'

function makeRouter() {
  const Stub = { template: '<div />' }
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Stub },
      { path: '/places/:id', name: 'place', component: Stub },
      { path: '/boards/:id', name: 'post', component: Stub },
    ],
  })
}

async function openWidget() {
  const router = makeRouter()
  router.push('/')
  await router.isReady()
  const w = mount(ChatWidget, { global: { plugins: [router] }, attachTo: document.body })
  await w.find('button[aria-label="챗봇 열기"]').trigger('click')
  return w
}

describe('ChatWidget', () => {
  beforeEach(() => {
    window.matchMedia = window.matchMedia || (() => ({ matches: false }))
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  test('renders the 4 suggestions', async () => {
    expect(CHAT_SUGGESTIONS).toHaveLength(4)
    const w = await openWidget()
    for (const s of CHAT_SUGGESTIONS) expect(w.text()).toContain(s)
    w.unmount()
  })

  test('place source links to detail and save button saves it', async () => {
    postChat.mockResolvedValue({ answer: '촉석루를 추천해요', sources: [{ type: 'place', id: 'jh-1', label: '촉석루' }, { type: 'post', id: '3', label: '후기' }] })
    fetchPlace.mockResolvedValue({ id: 'jh-1', title: '촉석루', category: 'sight', tags: [], lat: 35.19, lng: 128.08 })
    const w = await openWidget()
    await w.findAll('button').find((b) => b.text() === CHAT_SUGGESTIONS[0]).trigger('click')
    await flushPromises()
    expect(w.find('a[href="/places/jh-1"]').exists()).toBe(true)
    expect(w.find('a[href="/boards/3"]').exists()).toBe(true)
    const lanterns = useLanternsStore()
    expect(lanterns.isSaved('jh-1')).toBe(false)
    await w.find('[data-test="source-save"]').trigger('click')
    await flushPromises()
    expect(fetchPlace).toHaveBeenCalledWith('jh-1')
    expect(lanterns.isSaved('jh-1')).toBe(true)
    expect(lanterns.items['jh-1'].title).toBe('촉석루')
    w.unmount()
  })

  test('a failed send puts the text back in the input and the same chip can be sent again (C13)', async () => {
    postChat.mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ answer: '하연옥', sources: [] })
    const w = await openWidget()
    const input = w.find('#chat-input')
    await input.setValue('진주성 근처 냉면집')
    await input.trigger('keyup.enter')
    await flushPromises()
    expect(input.element.value).toBe('진주성 근처 냉면집')
    await input.trigger('keyup.enter')
    await flushPromises()
    expect(postChat).toHaveBeenCalledTimes(2)
    expect(input.element.value).toBe('')
    expect(w.text()).toContain('하연옥')
    w.unmount()
  })

  test('a fallback answer is labelled', async () => {
    postChat.mockResolvedValueOnce({ answer: '관련 장소: 하연옥', sources: [], fallback: true })
    const w = await openWidget()
    await w.findAll('button').find((b) => b.text() === CHAT_SUGGESTIONS[0]).trigger('click')
    await flushPromises()
    expect(w.find('[data-test="chat-fallback-note"]').exists()).toBe(true)
    w.unmount()
  })
})
