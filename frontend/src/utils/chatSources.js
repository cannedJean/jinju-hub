// Chat sources follow the API contract { type, id, label }.
// Map them to existing app routes only (no invented routes).
export function getChatSourceRoute(source) {
  if (!source) return null

  if (source.type === 'post') {
    return `/boards/${encodeURIComponent(String(source.id))}`
  }

  if (source.type === 'location') {
    return {
      path: '/places',
      query: { keyword: String(source.label || '').trim() },
    }
  }

  return null
}
