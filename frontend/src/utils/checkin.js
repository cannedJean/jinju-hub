import { haversineMeters } from './geo'

export const LIGHT_RADIUS_M = 150
export const MAX_ACCURACY_M = 200

const isNum = (n) => typeof n === 'number' && Number.isFinite(n)

export function canLight(place, pos) {
  if (!place || !isNum(place.lat) || !isNum(place.lng) || !pos || !isNum(pos.lat) || !isNum(pos.lng)) {
    return { ok: false, distance: NaN, reason: 'no_coords' }
  }
  const distance = haversineMeters(place, pos)
  // Unknown accuracy is not trusted.
  if (!isNum(pos.accuracy) || pos.accuracy > MAX_ACCURACY_M) {
    return { ok: false, distance, reason: 'low_accuracy' }
  }
  if (Math.max(0, distance - pos.accuracy) <= LIGHT_RADIUS_M) return { ok: true, distance, reason: 'ok' }
  return { ok: false, distance, reason: 'too_far' }
}

export function getPosition({ timeout = 10000 } = {}) {
  return new Promise((resolve, reject) => {
    const geo = globalThis.navigator?.geolocation
    if (!geo) return reject(new Error('unsupported'))
    geo.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: p.coords.accuracy }),
      (err) => reject(new Error(err && err.code === 1 ? 'permission_denied' : 'position_unavailable')),
      { enableHighAccuracy: true, timeout, maximumAge: 0 },
    )
  })
}
