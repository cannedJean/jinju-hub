import { beforeEach, describe, expect, test, vi } from 'vitest'
import { useChatStore } from '../chat'
import { useLanternsStore } from '../lanterns'
import { postChat } from '../../api/chat'

vi.mock('../../api/chat', () => ({ postChat: vi.fn() }))

const httpError = (status, detail) => Object.assign(new Error(`HTTP ${status}`), { response: { status, data: { detail } } })

describe('chat store', () => {
  beforeEach(() => {
    vi.resetAllMocks() // also drops queued mockResolvedValueOnce values a failing test left behind
    sessionStorage.clear()
  })

  test('429 shows a Korean message, never the raw rate_limited token (C12)', async () => {
    postChat.mockRejectedValueOnce(httpError(429, 'rate_limited'))
    const chat = useChatStore()
    await chat.send('진주성 냉면')
    expect(chat.error).toBe(true)
    expect(chat.errorMessage).not.toContain('rate_limited')
    expect(chat.errorMessage).toMatch(/잠시 후 다시 시도/)
  })

  test('resending the same text after a failure retries it instead of dropping it (C13)', async () => {
    postChat.mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ answer: '하연옥', sources: [] })
    const chat = useChatStore()
    expect(await chat.send('진주성 근처 냉면집 알려줘')).toBe(false)
    expect(await chat.send('진주성 근처 냉면집 알려줘')).toBe(true)
    expect(postChat).toHaveBeenCalledTimes(2)
    expect(chat.error).toBe(false)
    expect(chat.history.map((m) => [m.role, m.content])).toEqual([
      ['user', '진주성 근처 냉면집 알려줘'],
      ['assistant', '하연옥'],
    ])
  })

  test('the dangling failed question survives a reload and can still be sent again (C13)', async () => {
    postChat.mockRejectedValueOnce(new Error('timeout'))
    await useChatStore().send('남강 야경')
    // Simulate a reload: a fresh store restores the history from sessionStorage, the error box is gone.
    const { createPinia, setActivePinia } = await import('pinia')
    setActivePinia(createPinia())
    postChat.mockResolvedValueOnce({ answer: '남가람 별빛길', sources: [] })
    const chat = useChatStore()
    expect(chat.history.at(-1)).toEqual({ role: 'user', content: '남강 야경' })
    expect(await chat.send('남강 야경')).toBe(true)
    expect(postChat).toHaveBeenCalledTimes(2)
    expect(postChat.mock.calls[1][1]).toEqual([]) // the dangling copy is not sent as history
    expect(chat.history).toHaveLength(2)
  })

  test('a duplicate send while answered is still a new question', async () => {
    postChat.mockResolvedValue({ answer: '네', sources: [] })
    const chat = useChatStore()
    await chat.send('안녕')
    await chat.send('안녕')
    expect(postChat).toHaveBeenCalledTimes(2)
  })

  test('sends the demo reference date only in demo mode (C3/C21)', async () => {
    postChat.mockResolvedValue({ answer: '네', sources: [] })
    const chat = useChatStore()
    await chat.send('축제 있어?')
    expect(postChat.mock.calls[0][2]).toBeUndefined()
    useLanternsStore().setDemo({ enabled: true, today: '2026-10-10', pos: null })
    await chat.send('지금 진행 중인 축제 있어?')
    expect(postChat.mock.calls[1][2]).toBe('2026-10-10')
    useLanternsStore().setDemo({ enabled: false, today: '2026-10-10', pos: null })
    await chat.send('또 있어?')
    expect(postChat.mock.calls[2][2]).toBeUndefined()
  })

  test('keeps the fallback flag on the answer (C22)', async () => {
    postChat.mockResolvedValueOnce({ answer: '관련 장소: 하연옥', sources: [], fallback: true })
    const chat = useChatStore()
    await chat.send('냉면')
    expect(chat.history.at(-1).fallback).toBe(true)
    const { createPinia, setActivePinia } = await import('pinia')
    setActivePinia(createPinia())
    expect(useChatStore().history.at(-1).fallback).toBe(true)
  })
})
