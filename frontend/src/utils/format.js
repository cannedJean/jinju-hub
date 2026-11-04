export const CATEGORY_LABELS = {
  sight: '명소',
  culture: '문화·역사',
  food: '맛집',
  stay: '숙박',
  festival: '축제·행사',
  shopping: '쇼핑',
  leisure: '레포츠',
  course: '여행코스',
}

export function categoryLabel(code) {
  return CATEGORY_LABELS[code] ?? '기타'
}

// 650 -> "650m", 1234 -> "1.2km", null -> ""
export function formatDistance(m) {
  if (m === null || m === undefined || Number.isNaN(Number(m))) return ''
  const meters = Number(m)
  if (meters < 1000) return `${Math.round(meters)}m`
  return `${(meters / 1000).toFixed(1)}km`
}

function parts(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso ?? ''))
  if (!match) return null
  return { y: Number(match[1]), m: Number(match[2]), d: Number(match[3]) }
}

// ("2026-10-03","2026-10-18") -> "10.3 ~ 10.18"; different years -> "2026.12.31 ~ 2027.1.2"
export function formatDateRange(start, end) {
  const s = parts(start)
  const e = parts(end)
  if (!s && !e) return ''
  if (!s) return `~ ${e.m}.${e.d}`
  if (!e) return `${s.m}.${s.d} ~`
  if (s.y !== e.y) return `${s.y}.${s.m}.${s.d} ~ ${e.y}.${e.m}.${e.d}`
  return `${s.m}.${s.d} ~ ${e.m}.${e.d}`
}
