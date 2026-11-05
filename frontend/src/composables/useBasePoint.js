import { computed, onScopeDispose, ref } from 'vue'
import { useLanternsStore } from '../stores/lanterns'
import { demoPosition, haversineMeters, inJinjuBounds } from '../utils/geo'
import { formatDistance } from '../utils/format'

export const DEFAULT_RADIUS = 1000
export const GPS_ACCURACY_LIMIT_M = 200

const hasCoords = (p) => !!p && Number.isFinite(p.lat) && Number.isFinite(p.lng)
const sameSpot = (a, b) => hasCoords(a) && hasCoords(b) && haversineMeters(a, b) < 5

function defaultGeolocation() {
  return typeof navigator !== 'undefined' && 'geolocation' in navigator ? navigator.geolocation : null
}

// "내 숙소" base point for the explore view: the stored lodging (lantern store) plus the URL's
// near/radius. `state`/`update` come from useExploreQuery. Callbacks that arrive after the owning
// component unmounts (slow GPS) are dropped, so they never navigate or overwrite the lodging.
export function useBasePoint({ state, update, onBaseSet, geolocation = defaultGeolocation() }) {
  const lanterns = useLanternsStore()
  const picking = ref(false)
  const locating = ref(false)
  const message = ref('')
  let disposed = false
  onScopeDispose(() => {
    disposed = true
  })

  // Point shown on the map: the URL's `near` (labelled with the lodging name when it is the
  // lodging), otherwise the stored lodging.
  const refPoint = computed(() => {
    const near = state.value.near
    const base = lanterns.base
    if (near) return { lat: near.lat, lng: near.lng, label: sameSpot(base, near) ? base.label : '기준점' }
    return hasCoords(base) ? { lat: base.lat, lng: base.lng, label: base.label } : null
  })
  const activeRadius = computed(() => (state.value.near && state.value.radius ? state.value.radius : null))

  function setBase(point, note = '') {
    if (disposed) return
    picking.value = false
    message.value = note
    const base = { lat: point.lat, lng: point.lng, label: point.label || '내 숙소' }
    lanterns.setBase(base)
    update({
      near: { lat: base.lat, lng: base.lng },
      radius: state.value.radius || DEFAULT_RADIUS,
      sort: 'distance',
      bbox: null,
    })
    onBaseSet?.(base)
  }

  function setRadius(radius) {
    if (!refPoint.value) return
    if (!radius) {
      update({ near: null, radius: null })
      return
    }
    update({ near: { lat: refPoint.value.lat, lng: refPoint.value.lng }, radius, sort: 'distance', bbox: null })
  }

  function clearBase() {
    message.value = ''
    const near = state.value.near
    // A shared link's point is not the user's lodging: only forget the lodging when it is the one shown.
    if (lanterns.base && (!near || sameSpot(lanterns.base, near))) lanterns.setBase(null)
    update({ near: null, radius: null, sort: state.value.sort === 'distance' ? 'relevance' : state.value.sort })
  }

  function startPicking() {
    message.value = ''
    picking.value = true
  }

  function cancelPicking() {
    picking.value = false
  }

  function pickAt(point) {
    if (!inJinjuBounds(point)) return
    setBase({ ...point, label: '지도에서 고른 위치' })
  }

  function setFromPlace(place) {
    if (!hasCoords(place)) return
    setBase({ lat: place.lat, lng: place.lng, label: place.title })
  }

  function locate() {
    if (disposed) return
    message.value = ''
    const virtual = demoPosition(lanterns.demo)
    if (virtual) {
      setBase({ lat: virtual.lat, lng: virtual.lng, label: '내 숙소 (가상 위치)' })
      return
    }
    if (!geolocation) {
      message.value = '이 브라우저는 위치 기능을 지원하지 않아요. 지도에서 직접 찍어 주세요.'
      return
    }
    locating.value = true
    geolocation.getCurrentPosition(
      ({ coords }) => {
        if (disposed) return
        locating.value = false
        const point = { lat: coords.latitude, lng: coords.longitude }
        if (!inJinjuBounds(point)) {
          message.value = '현재 위치가 진주 밖이에요. 지도에서 숙소 위치를 찍어 주세요.'
          return
        }
        const note =
          coords.accuracy > GPS_ACCURACY_LIMIT_M
            ? `위치 정확도가 낮아요(±${formatDistance(coords.accuracy)}). 필요하면 지도에서 다시 찍어 주세요.`
            : ''
        setBase({ ...point, label: '현재 위치' }, note)
      },
      (err) => {
        if (disposed) return
        locating.value = false
        message.value =
          err?.code === 1
            ? '위치 권한이 거부되었어요. 지도에서 직접 찍어 주세요.'
            : '현재 위치를 확인하지 못했어요. 지도에서 직접 찍어 주세요.'
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  return {
    refPoint,
    activeRadius,
    picking,
    locating,
    message,
    setBase,
    setRadius,
    clearBase,
    startPicking,
    cancelPicking,
    pickAt,
    setFromPlace,
    locate,
  }
}
