import { defineStore } from 'pinia'
import { loadState, saveState, storageReadable } from '../utils/lanternStorage'

// KST (Asia/Seoul) calendar date as YYYY-MM-DD. `now` is injectable for tests.
export function kstToday(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(now)
}

// True while restore() runs, so listeners can tell an undo from a genuinely new light.
let restoring = false
export const isRestoring = () => restoring

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
  hero_image: p.hero_image ?? null,
  summary: p.summary ?? p.addr ?? null,
  addr: p.addr ?? null,
  jinju8_rank: p.jinju8_rank ?? null,
  is_collection: p.is_collection ?? null,
})

export const useLanternsStore = defineStore('lanterns', {
  state: () => ({ ...loadState(), storageAvailable: storageReadable() }),
  getters: {
    isSaved: (s) => (id) => !!s.items[id],
    isLit: (s) => (id) => !!s.items[id]?.litAt,
    savedList: (s) =>
      Object.values(s.items).sort((a, b) => {
        const diff = (b.savedAt || '').localeCompare(a.savedAt || '')
        if (diff !== 0) return diff
        return (a.id || '').localeCompare(b.id || '')
      }),
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
    // Undo for unsave: puts back the full snapshot (incl. lit fields).
    restore(item) {
      if (!item?.id || this.items[item.id]) return
      restoring = true
      try {
        this.items[item.id] = { ...item }
      } finally {
        restoring = false
      }
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
    verify(places = []) {
      const list = Array.isArray(places) ? places : (places ? [places] : [])
      let changed = false
      for (const [id, cur] of Object.entries(this.items)) {
        if (
          cur.hero_image === undefined ||
          cur.summary === undefined ||
          cur.addr === undefined ||
          cur.jinju8_rank === undefined ||
          cur.is_collection === undefined
        ) {
          this.items[id] = {
            ...cur,
            hero_image: cur.hero_image ?? null,
            summary: cur.summary ?? cur.addr ?? null,
            addr: cur.addr ?? null,
            jinju8_rank: cur.jinju8_rank ?? null,
            is_collection: cur.is_collection ?? null,
          }
          changed = true
        }
      }
      for (const p of list) {
        if (!p?.id || !this.items[p.id]) continue
        const cur = this.items[p.id]
        const updated = {
          ...cur,
          hero_image: cur.hero_image ?? p.hero_image ?? null,
          summary: cur.summary ?? p.summary ?? p.addr ?? null,
          addr: cur.addr ?? p.addr ?? null,
          jinju8_rank: cur.jinju8_rank ?? p.jinju8_rank ?? null,
          is_collection: cur.is_collection ?? p.is_collection ?? null,
          lat: cur.lat ?? p.lat ?? null,
          lng: cur.lng ?? p.lng ?? null,
          category: cur.category ?? p.category ?? null,
          title: cur.title ?? p.title ?? p.id,
        }
        if (
          cur.hero_image !== updated.hero_image ||
          cur.summary !== updated.summary ||
          cur.addr !== updated.addr ||
          cur.jinju8_rank !== updated.jinju8_rank ||
          cur.is_collection !== updated.is_collection
        ) {
          this.items[p.id] = updated
          changed = true
        }
      }
      if (changed) this.persist()
    },
  },
})
