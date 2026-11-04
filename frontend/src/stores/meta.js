import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMeta } from '../api/places'

// Dataset metadata (data_version, generated_at, attribution); loaded once, failures are non-fatal.
export const useMetaStore = defineStore('meta', () => {
  const data = ref(null)
  let pending = null

  function load() {
    if (data.value) return Promise.resolve(data.value)
    pending ??= fetchMeta()
      .then((d) => (data.value = d))
      .catch(() => null)
      .finally(() => {
        pending = null
      })
    return pending
  }

  return { data, load }
})
