import apiClient from './client'

export function postChat(message, history = []) {
  return apiClient.post('/chat', { message, history }, { timeout: 30_000 }).then((res) => res.data)
}
