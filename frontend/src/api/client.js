import axios from 'axios'

const apiBaseUrl = String(import.meta.env.VITE_API_BASE_URL ?? '')
  .trim()
  .replace(/\/+$/, '')

const WARM_TIMEOUT_MS = 12_000
// Render's free plan sleeps after idling and needs ~50 s to wake: until the server has answered once,
// wait that long instead of failing at 12 s.
const COLD_TIMEOUT_MS = 60_000
const WAKING_HINT_AFTER_MS = 5_000
const RETRY_DELAY_MS = 2_000
const WAKING_STATUS = new Set([502, 503, 504])

const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: WARM_TIMEOUT_MS,
})

// ---- cold-start handling -------------------------------------------------------------------
let awake = false
let wakingShown = false
const wakingConfigs = new Set()
const coldTimers = new Map()
const listeners = new Set()

function publishWaking() {
  const next = wakingConfigs.size > 0
  if (next === wakingShown) return
  wakingShown = next
  listeners.forEach((fn) => fn(next))
}

// Requests are tracked by an id stored on the config: axios copies configs on request(), so the retry
// is a different object from the one that failed.
let nextId = 0
function settle(config) {
  const id = config?.__wid
  if (id === undefined) return
  clearTimeout(coldTimers.get(id))
  coldTimers.delete(id)
  wakingConfigs.delete(id)
  publishWaking()
}

// Subscribe to the "server is waking up" state (true after ~5 s of a cold request, or during the
// automatic retry). Returns an unsubscribe function.
export function onColdStart(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function resetColdStart() {
  awake = false
  wakingShown = false
  wakingConfigs.clear()
  coldTimers.forEach((t) => clearTimeout(t))
  coldTimers.clear()
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function isWakeFailure(error) {
  if (error?.response) return WAKING_STATUS.has(error.response.status)
  return ['ECONNABORTED', 'ETIMEDOUT', 'ERR_NETWORK'].includes(error?.code)
}

apiClient.interceptors.request.use((config) => {
  config.__wid ??= ++nextId
  if (!awake) {
    config.timeout = COLD_TIMEOUT_MS
    if (!config.__retried) {
      const id = config.__wid
      coldTimers.set(
        id,
        setTimeout(() => {
          wakingConfigs.add(id)
          publishWaking()
        }, WAKING_HINT_AFTER_MS),
      )
    }
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => {
    awake = true
    settle(response.config)
    return response
  },
  async (error) => {
    const config = error?.config
    const retry = !!config && !config.__retried && String(config.method).toLowerCase() === 'get' && isWakeFailure(error)
    if (!retry) {
      settle(config)
      if (error?.response) awake = true
      return Promise.reject(error)
    }
    // One automatic retry for idempotent GETs while the server wakes up.
    config.__retried = true
    clearTimeout(coldTimers.get(config.__wid))
    coldTimers.delete(config.__wid)
    wakingConfigs.add(config.__wid)
    publishWaking()
    await sleep(RETRY_DELAY_MS)
    return apiClient.request(config)
  },
)

export const RATE_LIMIT_MESSAGE = '잠시 후 다시 시도해 주세요.'

export function getApiStatus(error) {
  return error?.response?.status ?? 0
}

export function getApiDetail(error, fallback = '요청을 처리하지 못했습니다.') {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join(' ') || fallback
  }

  return error?.response?.data?.message || fallback
}

// Maps FastAPI 422 validation errors ({ detail: [{ loc, msg }] }) to a field->message object.
export function getValidationErrors(error) {
  const detail = error?.response?.data?.detail
  if (!Array.isArray(detail)) return {}

  return detail.reduce((errors, issue) => {
    const field = issue?.loc?.at(-1)
    if (typeof field === 'string' && typeof issue?.msg === 'string') {
      errors[field] = issue.msg
    }
    return errors
  }, {})
}

export default apiClient
