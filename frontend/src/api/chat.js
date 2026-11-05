import apiClient from './client'

// `today` (YYYY-MM-DD) is the demo reference date; the backend honours it only in demo mode.
// The 30 s timeout stays above the backend's budget (Claude 20 s + weather 3 s + retrieval).
export function postChat(message, history = [], today = undefined) {
  const body = { message, history, ...(today ? { today } : {}) }
  return apiClient.post('/chat', body, { timeout: 30_000 }).then((res) => res.data)
}
