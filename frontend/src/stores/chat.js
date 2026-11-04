import { defineStore } from 'pinia'
import { ref } from 'vue'
import { postChat } from '../api/chat'
import { getApiDetail } from '../api/client'

const STORAGE_KEY = 'localhub_chat'

// Guard against malformed sessionStorage so a bad value can never crash the app.
function loadHistory() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    if (!Array.isArray(parsed)) return []

    return parsed
      .filter(
        (item) =>
          item &&
          (item.role === 'user' || item.role === 'assistant') &&
          typeof item.content === 'string',
      )
      .map((item) => ({
        role: item.role,
        content: item.content,
        ...(item.role === 'assistant' && Array.isArray(item.sources)
          ? { sources: item.sources }
          : {}),
      }))
  } catch {
    return []
  }
}

export const useChatStore = defineStore('chat', () => {
  const history = ref(loadHistory())
  const loading = ref(false)
  const error = ref(false)
  const errorMessage = ref('')
  let lastAttempt = ''

  function persist() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history.value))
    } catch {
      /* ignore quota/serialization errors */
    }
  }

  async function send(text, { retry = false } = {}) {
    const message = String(text ?? '').trim()
    if (!message || loading.value) return

    const last = history.value[history.value.length - 1]
    if (retry && last?.role === 'user' && last.content === message) {
      history.value.pop()
    }

    // Block accidental duplicate sends while preserving an explicit retry.
    const currentLast = history.value[history.value.length - 1]
    if (currentLast?.role === 'user' && currentLast.content === message) return

    lastAttempt = message
    error.value = false
    errorMessage.value = ''
    history.value.push({ role: 'user', content: message })
    persist()
    loading.value = true

    try {
      const priorHistory = history.value
        .slice(0, -1)
        .slice(-20)
        .map((m) => ({ role: m.role, content: m.content }))
      const data = await postChat(message, priorHistory)
      history.value.push({
        role: 'assistant',
        content: data?.answer ?? '',
        sources: Array.isArray(data?.sources) ? data.sources : [],
      })
      persist()
    } catch (e) {
      error.value = true
      errorMessage.value = getApiDetail(e, '네트워크 오류가 발생했습니다. 다시 시도해 주세요.')
    } finally {
      loading.value = false
    }
  }

  function retry() {
    if (lastAttempt) send(lastAttempt, { retry: true })
  }

  function clear() {
    history.value = []
    persist()
  }

  return { history, loading, error, errorMessage, send, retry, clear }
})
