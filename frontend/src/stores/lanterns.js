import { defineStore } from 'pinia'
import { loadState, saveState, storageReadable } from '../utils/lanternStorage'

// KST (Asia/Seoul) calendar date as YYYY-MM-DD. `now` is injectable for tests.
export function kstToday(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(now)
}

let nowProvider = () => new Date()
export function setNowProvider(fn) {
  nowProvider = fn || (() => new Date())
}

const snapshot = (p) => ({
  id: p.id,
  title: p.title ?? p.id,
  category: p.category ?? null,
  tags: p.tags ?? [],
  lat: p.lat ?? null,
  lng: p.lng ?? null,
})

export const useLanternsStore = defineStore('lanterns', {
  state: () => ({ ...loadState(), storageAvailable: storageReadable() }),
  getters: {
    isSaved: (s) => (id) => !!s.items[id],
    isLit: (s) => (id) => !!s.items[id]?.litAt,
    savedList: (s) => Object.values(s.items).sort((a, b) => (b.savedAt || '').localeCompare(a.savedAt || '')),
    litCount: (s) => Object.values(s.items).filter((it) => it.litAt).length,
    effectiveToday: (s) => (s.demo.enabled && s.demo.today ? s.demo.today : kstToday(nowProvider())),
  },
  actions: {
    persist() {
      const { storageAvailable, ...data } = this.$state
      this.storageAvailable = saveState(JSON.parse(JSON.stringify(data)))
    },
    _put(summary) {
      const prev = this.items[summary.id]
      this.items[summary.id] = {
        ...prev,
        ...snapshot(summary),
        savedAt: prev?.savedAt || new Date().toISOString(),
      }
    },
    save(summary) {
      this._put(summary)
      this.persist()
    },
    unsave(id) {
      delete this.items[id]
      this.persist()
    },
    light(id, method, summary) {
      if (!this.items[id]) this._put(summary || { id, title: id })
      if (this.items[id].litAt) return
      Object.assign(this.items[id], {
        litAt: new Date().toISOString(),
        litOn: this.effectiveToday,
        litMethod: method,
      })
      this.persist()
    },
    setBase(base) {
      this.base = base
      this.persist()
    },
    setDemo({ enabled, today = null, pos = null }) {
      this.demo = { enabled: !!enabled, today, pos }
      this.persist()
    },
    markBadgeEarned(id) {
      if (this.earnedBadges[id]) return
      this.earnedBadges[id] = new Date().toISOString()
      this.persist()
    },
    migrateId(oldId, newId) {
      const it = this.items[oldId]
      if (!it || oldId === newId) return
      const cur = this.items[newId]
      if (!cur) {
        this.items[newId] = { ...it, id: newId }
      } else {
        const merged = { ...cur }
        if (it.savedAt && (!cur.savedAt || it.savedAt < cur.savedAt)) merged.savedAt = it.savedAt
        if (it.litAt && (!cur.litAt || it.litAt < cur.litAt)) {
          merged.litAt = it.litAt
          merged.litOn = it.litOn
          merged.litMethod = it.litMethod
        }
        this.items[newId] = merged
      }
      delete this.items[oldId]
      this.persist()
    },
    importShared(ids, summariesById = {}) {
      for (const id of ids) {
        if (this.items[id]) continue
        this._put(summariesById[id] || { id, title: id })
      }
      this.persist()
    },
  },
})
