import { defineStore } from 'pinia'
import { markRaw } from 'vue'
import { fetchMarkers } from '../api/places'

let inflight = null

const hasCoords = (p) => !!p && Number.isFinite(p.lat) && Number.isFinite(p.lng)

// The user's saved/lit places stay on the map whatever the filters are. Live marker data wins;
// the stored snapshot covers places that are no longer in the marker list.
export function mergeUserMarkers(markers, lanternItems, byId) {
  const present = new Set(markers.map((m) => m.id))
  const extra = []
  for (const [id, item] of Object.entries(lanternItems || {})) {
    if (present.has(id)) continue
    const live = byId?.get(id)
    if (live) extra.push(live)
    else if (hasCoords(item)) {
      extra.push({ id, title: item.title ?? id, category: item.category, lat: item.lat, lng: item.lng, is_collection: false })
    }
  }
  return extra.length ? [...markers, ...extra] : markers
}

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
