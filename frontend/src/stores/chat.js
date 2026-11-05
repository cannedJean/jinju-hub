import { defineStore } from 'pinia'
import { ref } from 'vue'
import { postChat } from '../api/chat'
import { getApiDetail, getApiStatus, RATE_LIMIT_MESSAGE } from '../api/client'
import { useLanternsStore } from './lanterns'

const STORAGE_KEY = 'jinjuhub.chat.v1'
const CHAT_RATE_LIMIT_MESSAGE = `질문이 많아 잠시 쉬어 가요. ${RATE_LIMIT_MESSAGE}`

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
        ...(item.role === 'assistant' && item.fallback === true ? { fallback: true } : {}),
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

  // The demo reference date (if demo mode sets one), so chat agrees with the festival screens.
  function demoToday() {
    const { demo } = useLanternsStore()
    return demo?.enabled && demo.today ? demo.today : undefined
  }

  // Resolves to true when an answer arrived, false when nothing was sent or the request failed.
  async function send(text) {
    const message = String(text ?? '').trim()
    if (!message || loading.value) return false

    // Sending the unanswered last question again (after a failure or a reload) retries it.
    const last = history.value[history.value.length - 1]
    if (last?.role === 'user' && last.content === message) history.value.pop()

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
      const data = await postChat(message, priorHistory, demoToday())
      history.value.push({
        role: 'assistant',
        content: data?.answer ?? '',
        sources: Array.isArray(data?.sources) ? data.sources : [],
        ...(data?.fallback === true ? { fallback: true } : {}),
      })
      persist()
      return true
    } catch (e) {
      error.value = true
      errorMessage.value =
        getApiStatus(e) === 429
          ? CHAT_RATE_LIMIT_MESSAGE
          : getApiDetail(e, '네트워크 오류가 발생했습니다. 다시 시도해 주세요.')
      return false
    } finally {
      loading.value = false
    }
  }

  function retry() {
    return lastAttempt ? send(lastAttempt) : Promise.resolve(false)
  }

  function clear() {
    history.value = []
    persist()
  }

  return { history, loading, error, errorMessage, send, retry, clear }
})
