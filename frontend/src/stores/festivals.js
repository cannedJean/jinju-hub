import { defineStore } from 'pinia'
import { fetchFestivals } from '../api/places'
import { useLanternsStore } from './lanterns'

export const useFestivalsStore = defineStore('festivals', {
  state: () => ({ items: [], today: '', loading: false, error: false, loaded: false }),
  getters: {
    ongoing: (s) => s.items.filter((f) => f.status === 'ongoing'),
    upcoming: (s) => s.items.filter((f) => f.status === 'upcoming'),
    // Ended, stale (no recent edition) and undecided dates all read as "지난 축제".
    past: (s) => s.items.filter((f) => ['ended', 'stale', 'undecided'].includes(f.status)),
  },
  actions: {
    // Re-run whenever the demo date changes; the latest request wins.
    async load() {
      const lanterns = useLanternsStore()
      const today = lanterns.demo.enabled && lanterns.demo.today ? lanterns.demo.today : undefined
      const seq = (this._seq = (this._seq || 0) + 1)
      this.loading = true
      this.error = false
      try {
        const res = await fetchFestivals({ status: 'all', today })
        if (seq !== this._seq) return
        this.items = res?.items || []
        this.today = res?.today || ''
        this.loaded = true
      } catch {
        if (seq !== this._seq) return
        this.error = true
      } finally {
        if (seq === this._seq) this.loading = false
      }
    },
  },
})
