import axios from 'axios'

const apiBaseUrl = String(import.meta.env.VITE_API_BASE_URL ?? '')
  .trim()
  .replace(/\/+$/, '')

const apiClient = axios.create({
  baseURL: `${apiBaseUrl}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 12_000,
})

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
