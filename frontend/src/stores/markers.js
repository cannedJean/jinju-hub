import { defineStore } from 'pinia'
import { markRaw } from 'vue'
import { fetchMarkers } from '../api/places'

let inflight = null

// All map markers (~1,250 places with coordinates), loaded once per session and filtered client-side.
export const useMarkersStore = defineStore('markers', {
  state: () => ({ items: [], loaded: false, error: false }),
  getters: {
    byId: (s) => new Map(s.items.map((m) => [m.id, m])),
    counts: (s) => {
      const out = {}
      for (const m of s.items) out[m.category] = (out[m.category] || 0) + 1
      return out
    },
    byCategory: (s) => (categories) => {
      if (!categories?.length) return s.items
      const wanted = new Set(categories)
      return s.items.filter((m) => wanted.has(m.category))
    },
  },
  actions: {
    // Concurrent callers share one request; a failure leaves the store retryable.
    async load() {
      if (this.loaded) return
      if (!inflight) {
        inflight = fetchMarkers()
          .then((data) => {
            // Read-only list: skip deep reactivity for ~1k objects.
            this.items = markRaw(Array.isArray(data) ? data : [])
            this.loaded = true
            this.error = false
          })
          .catch((err) => {
            this.error = true
            throw err
          })
          .finally(() => {
            inflight = null
          })
      }
      await inflight
    },
  },
})
