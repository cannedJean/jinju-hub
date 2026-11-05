const R = 6371008.8

// Default demo-mode virtual position (촉석루): the pin shown on the map until the presenter drags it.
export const DEMO_START = { lat: 35.1897, lng: 128.0819 }

// The effective demo position: the dragged pin when set, otherwise DEMO_START (null outside demo mode).
export function demoPosition(demo) {
  if (!demo?.enabled) return null
  const p = demo.pos
  return p && Number.isFinite(p.lat) && Number.isFinite(p.lng) ? p : DEMO_START
}

const rad = (d) => (d * Math.PI) / 180

export function haversineMeters(a, b) {
  const dLat = rad(b.lat - a.lat)
  const dLng = rad(b.lng - a.lng)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)))
}

// Leaflet LatLngBounds -> "minLng,minLat,maxLng,maxLat" (5 decimals)
export function boundsToBbox(bounds) {
  return [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]
    .map((n) => n.toFixed(5))
    .join(',')
}

// Two points (SW, NE) spanning a circle of `meters` around `center` — for fitting the map to a radius.
export function radiusFitPoints(center, meters) {
  const dLat = (meters / R) * (180 / Math.PI)
  const dLng = dLat / Math.cos(rad(center.lat))
  return [
    { lat: center.lat - dLat, lng: center.lng - dLng },
    { lat: center.lat + dLat, lng: center.lng + dLng },
  ]
}

// "minLng,minLat,maxLng,maxLat" -> [SW, NE] points, or null.
export function bboxToPoints(bbox) {
  if (!bbox) return null
  const [minLng, minLat, maxLng, maxLat] = String(bbox).split(',').map(Number)
  return [
    { lat: minLat, lng: minLng },
    { lat: maxLat, lng: maxLng },
  ]
}

// Jinju region bbox (lat 35.05~35.33, lng 127.93~128.30) + 0.05 deg margin, as Leaflet [[S, W], [N, E]].
export const JINJU_MAX_BOUNDS = [
  [35.0, 127.88],
  [35.38, 128.35],
]

export function inJinjuBounds({ lat, lng }) {
  const [[s, w], [n, e]] = JINJU_MAX_BOUNDS
  return lat >= s && lat <= n && lng >= w && lng <= e
}
