import { defineStore } from 'pinia'
import { fetchCollection } from '../api/places'
import { evaluateBadges } from '../utils/badges'
import { useLanternsStore } from './lanterns'

let inflight = null

export const useCollectionStore = defineStore('collection', {
  state: () => ({ data: null, loaded: false, error: false, newlyEarned: [] }),
  getters: {
    collectionIds: (s) => s.data?.collection_ids || [],
    badges: (s) => s.data?.badges || [],
    progress() {
      const lanterns = useLanternsStore()
      return this.collectionIds.filter((id) => lanterns.isLit(id)).length
    },
    evaluated() {
      return evaluateBadges(useLanternsStore().$state, this.data)
    },
  },
  actions: {
    // Fetches /api/collection once; concurrent calls share one request, failures can be retried.
    async load() {
      if (this.loaded) return
      if (!inflight) {
        inflight = fetchCollection()
          .then((d) => {
            this.data = d
            this.loaded = true
            this.error = false
          })
          .catch((e) => {
            this.error = true
            throw e
          })
          .finally(() => {
            inflight = null
          })
      }
      await inflight
    },
    // Records badges earned since last check (persisted, so each toasts once) and queues them.
    checkBadges() {
      const lanterns = useLanternsStore()
      for (const b of this.evaluated) {
        if (b.earned && !lanterns.earnedBadges[b.id]) {
          lanterns.markBadgeEarned(b.id)
          this.newlyEarned.push(b)
        }
      }
      return this.newlyEarned
    },
    consumeNewlyEarned() {
      const q = this.newlyEarned
      this.newlyEarned = []
      return q
    },
  },
})
