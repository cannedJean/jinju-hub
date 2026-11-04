import { defineStore } from 'pinia'
import { ref } from 'vue'

// One-time, in-memory transport for the edit password from the detail modal to the edit form.
// Never persisted to storage or the URL. The PUT request is what actually verifies it (403 on mismatch).
export const usePostAuthStore = defineStore('postAuth', () => {
  const passwords = ref(new Map())

  function remember(postId, password) {
    passwords.value.set(String(postId), password)
  }

  function take(postId) {
    const key = String(postId)
    const password = passwords.value.get(key) || ''
    passwords.value.delete(key)
    return password
  }

  function forget(postId) {
    passwords.value.delete(String(postId))
  }

  function clear() {
    passwords.value.clear()
  }

  return { remember, take, forget, clear }
})
