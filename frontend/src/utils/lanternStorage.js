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
      items: data.items,
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
