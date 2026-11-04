import L from 'leaflet'
import { CATEGORY_LABELS } from '../../utils/format'

// Marker / cluster icons for the explore map. All HTML here is static markup built from our own
// constants — place data (titles etc.) never goes into an icon's html, only into textContent/title.

const STATES = ['none', 'saved', 'lit']

export function safeCategory(category) {
  return Object.hasOwn(CATEGORY_LABELS, category) ? category : 'etc'
}

export function markerState(id, savedIds, litIds) {
  if (litIds?.has(id)) return 'lit'
  if (savedIds?.has(id)) return 'saved'
  return 'none'
}

const PIN_SVG = (collection) =>
  '<svg class="marker-pin" viewBox="0 0 28 36" width="28" height="36" aria-hidden="true" focusable="false">' +
  '<path class="marker-pin__body" d="M14 1.5C7.1 1.5 1.8 6.8 1.8 13.5c0 8.6 12.2 20.9 12.2 20.9s12.2-12.3 12.2-20.9C26.2 6.8 20.9 1.5 14 1.5z"/>' +
  (collection
    ? '<path class="marker-pin__mark" d="M14 7.8l5 5.6-5 5.6-5-5.6z"/>'
    : '<circle class="marker-pin__dot" cx="14" cy="13.4" r="4.6"/>') +
  '</svg>'

// 유등 (floating lantern). Outline = 담음 ◇, filled = 밝힘 ◆.
const LANTERN_SVG = (variant) =>
  `<svg class="lantern lantern--${variant}" viewBox="0 0 30 40" width="30" height="40" aria-hidden="true" focusable="false">` +
  '<path class="lantern__string" d="M15 0.5v4"/>' +
  '<rect class="lantern__cap" x="10" y="4" width="10" height="3.6" rx="1.2"/>' +
  '<path class="lantern__body" d="M7.5 8h15c3.6 0 6.5 2.9 6.5 6.5v7c0 3.6-2.9 6.5-6.5 6.5h-15C3.9 28 1 25.1 1 21.5v-7C1 10.9 3.9 8 7.5 8z"/>' +
  '<path class="lantern__rib" d="M9.5 8.6c-2.2 4.2-2.2 14.6 0 18.8M20.5 8.6c2.2 4.2 2.2 14.6 0 18.8"/>' +
  '<path class="lantern__mark" d="M15 12.6l4.4 5.4-4.4 5.4-4.4-5.4z"/>' +
  '<rect class="lantern__cap" x="10" y="28.4" width="10" height="3.6" rx="1.2"/>' +
  '<path class="lantern__tassel" d="M15 32v6.5"/>' +
  '</svg>'

export function makeMarkerIcon({ category, state = 'none', highlighted = false, collection = false } = {}) {
  const st = STATES.includes(state) ? state : 'none'
  const classes = ['jh-marker', `marker--${safeCategory(category)}`, `marker--${st}`]
  if (highlighted) classes.push('marker--active')
  if (collection) classes.push('marker--collection')

  const isLantern = st !== 'none'
  const inner = isLantern
    ? (st === 'lit' ? '<span class="lantern-glow" aria-hidden="true"></span>' : '') +
      LANTERN_SVG(st === 'lit' ? 'filled' : 'outline')
    : PIN_SVG(collection)

  return L.divIcon({
    className: classes.join(' '),
    html: `<div class="marker__inner">${inner}</div>`,
    iconSize: isLantern ? [30, 40] : [28, 36],
    iconAnchor: isLantern ? [15, 39] : [14, 35],
    popupAnchor: [0, -34],
  })
}

// Accessible marker options: the place name doubles as tooltip and accessible name; keyboard
// focusable so Tab reaches markers and Enter selects them.
export function buildMarkerOptions(marker) {
  return { title: marker.title, alt: marker.title, keyboard: true }
}

// Category mix of a cluster -> donut segments (percent ranges) + majority category.
export function clusterSummary(categories) {
  const counts = new Map()
  for (const c of categories) {
    const key = safeCategory(c)
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  const total = categories.length
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1])
  let acc = 0
  const segments = sorted.map(([category, count]) => {
    const from = acc
    acc += count
    return { category, count, from: Math.round((from / total) * 1000) / 10, to: Math.round((acc / total) * 1000) / 10 }
  })
  return { total, majority: sorted[0]?.[0] ?? 'etc', segments }
}

export function makeClusterIcon(categories) {
  const { total, majority, segments } = clusterSummary(categories)
  const gradient = segments.map((s) => `var(--cat-${s.category}, #64748b) ${s.from}% ${s.to}%`).join(', ')
  const size = total < 10 ? 38 : total < 100 ? 46 : 54
  const sizeClass = total < 10 ? 'sm' : total < 100 ? 'md' : 'lg'
  return L.divIcon({
    className: `jh-cluster cluster--${majority} cluster--${sizeClass}`,
    html:
      `<div class="cluster__ring" style="background: conic-gradient(${gradient})">` +
      `<span class="cluster__count" aria-hidden="true">${total}</span></div>` +
      `<span class="sr-only">장소 ${total}곳 묶음, Enter로 확대</span>`,
    iconSize: [size, size],
  })
}
