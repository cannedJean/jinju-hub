// Community post categories. `id` is the single source of truth shared with the backend.
export const POST_CATEGORIES = [
  { id: 'tour', label: '관광지', color: 'cat-badge-tour' },
  { id: 'food', label: '맛집', color: 'cat-badge-food' },
  { id: 'festival', label: '축제', color: 'cat-badge-festival' },
  { id: 'free', label: '자유게시판', color: 'cat-badge-free' },
]

const POST_CATEGORY_MAP = new Map(POST_CATEGORIES.map((c) => [c.id, c]))

export function getCategoryLabel(id) {
  return POST_CATEGORY_MAP.get(id)?.label || '분류없음'
}

export function getCategoryColor(id) {
  return POST_CATEGORY_MAP.get(id)?.color || 'cat-badge-free'
}

// Pipeline source keys (place_images.source / place_sources.source) -> user-facing names.
export const SOURCE_LABELS = {
  'jinju_city.tourinfo': '진주시 관광정보',
  'jinju_city.restaurant': '진주시 음식점 정보',
  'jinju_city.festival': '진주시 축제 정보',
  'jinju_city.heritage': '진주시 문화재 정보',
  'jinju_city.lodging': '진주시 숙박 정보',
  'tourapi.area': '한국관광공사 지역 관광정보',
  'tourapi.festival': '한국관광공사 행사정보',
}

export function sourceLabel(key) {
  return SOURCE_LABELS[key] || key || ''
}

function pad(value) {
  return String(value).padStart(2, '0')
}

// "2026.07.14 21:30" — tolerant of missing/invalid dates.
export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// "2026.07.14"
export function formatDateShort(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
}
