export const STORAGE_KEY = 'jinjuhub.lanterns.v1'

export function emptyState() {
  return {
    version: 1,
    items: {},
    base: null,
    demo: { enabled: false, today: null, pos: null },
    earnedBadges: {},
  }
}

const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v)

function defaultStorage() {
  try {
    return globalThis.localStorage
  } catch {
    return undefined
  }
}

const str = (v) => (typeof v === 'string' ? v : null)

// Keep only object entries with a usable id; normalize timestamp fields to string|null.
function cleanItems(items) {
  const out = {}
  for (const [key, it] of Object.entries(items)) {
    if (!isObj(it)) continue
    const id = typeof it.id === 'string' && it.id ? it.id : key
    out[key] = {
      ...it,
      id,
      tags: Array.isArray(it.tags) ? it.tags : [],
      savedAt: str(it.savedAt),
      litAt: str(it.litAt),
      litOn: str(it.litOn),
    }
  }
  return out
}

export function storageReadable(storage = defaultStorage()) {
  try {
    storage.getItem(STORAGE_KEY)
    return true
  } catch {
    return false
  }
}

// Never throws: missing / corrupted / wrong-version / inaccessible storage -> emptyState().
export function loadState(storage = defaultStorage()) {
  try {
    const raw = storage.getItem(STORAGE_KEY)
    if (!raw) return emptyState()
    const data = JSON.parse(raw)
    if (!isObj(data) || data.version !== 1 || !isObj(data.items)) return emptyState()
    const base = emptyState()
    return {
      version: 1,
      items: cleanItems(data.items),
      base: isObj(data.base) ? data.base : null,
      demo: { ...base.demo, ...(isObj(data.demo) ? data.demo : {}) },
      earnedBadges: isObj(data.earnedBadges) ? data.earnedBadges : {},
    }
  } catch {
    return emptyState()
  }
}

// Returns false (never throws) when storage is unavailable or full.
export function saveState(state, storage = defaultStorage()) {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(state))
    return true
  } catch {
    return false
  }
}
