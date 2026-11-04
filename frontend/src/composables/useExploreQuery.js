import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CATEGORY_LABELS } from '../utils/format'

// URL <-> explore state. The URL is the single source of truth for the explore query, so links,
// reloads and the back button all reproduce the same view.

export const CATEGORY_CODES = Object.keys(CATEGORY_LABELS)
export const TAG_CODES = ['indoor', 'outdoor', 'night_view', 'local_food', 'festival_venue']
export const SORTS = ['relevance', 'distance', 'name', 'collection']
export const RADII = [500, 1000, 3000, 5000]
export const PAGE_SIZE = 20

export const DEFAULT_STATE = Object.freeze({
  q: '',
  categories: Object.freeze([]),
  tags: Object.freeze([]),
  bbox: null,
  near: null,
  radius: null,
  sort: 'relevance',
  page: 1,
})

const first = (v) => (Array.isArray(v) ? v[0] : v)

// "a,b" or ["a", "b,c"] -> unique allowed codes, in order.
function codes(raw, allowed) {
  const parts = (Array.isArray(raw) ? raw : [raw])
    .filter((v) => typeof v === 'string')
    .flatMap((v) => v.split(','))
    .map((v) => v.trim())
  return [...new Set(parts.filter((v) => allowed.includes(v)))]
}

function numbers(raw, n) {
  if (typeof raw !== 'string') return null
  const parts = raw.split(',')
  if (parts.length !== n || parts.some((p) => p.trim() === '')) return null
  const nums = parts.map(Number)
  return nums.every(Number.isFinite) ? nums : null
}

function parseNear(raw) {
  const nums = numbers(first(raw), 2)
  if (!nums) return null
  const [lat, lng] = nums
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
  return { lat, lng }
}

function parseBbox(raw) {
  const nums = numbers(first(raw), 4)
  if (!nums) return null
  const [minLng, minLat, maxLng, maxLat] = nums
  if (minLng >= maxLng || minLat >= maxLat) return null
  if (Math.abs(minLat) > 90 || Math.abs(maxLat) > 90 || Math.abs(minLng) > 180 || Math.abs(maxLng) > 180) return null
  return nums.join(',')
}

function parseIntIn(raw, valid) {
  const s = first(raw)
  if (typeof s !== 'string' || !/^\d+$/.test(s.trim())) return null
  const n = Number(s)
  return valid(n) ? n : null
}

const round6 = (n) => Number(n.toFixed(6))
export const pointToString = (p) => `${round6(p.lat)},${round6(p.lng)}`

export function parseQuery(routeQuery = {}) {
  const rq = routeQuery || {}
  const q = first(rq.q)
  const sort = first(rq.sort)
  return {
    q: typeof q === 'string' ? q.trim().slice(0, 200) : '',
    categories: codes(rq.cat, CATEGORY_CODES),
    tags: codes(rq.tags, TAG_CODES),
    bbox: parseBbox(rq.bbox),
    near: parseNear(rq.near),
    radius: parseIntIn(rq.radius, (n) => RADII.includes(n)),
    sort: SORTS.includes(sort) ? sort : DEFAULT_STATE.sort,
    page: parseIntIn(rq.page, (n) => n >= 1) ?? 1,
  }
}

// State -> route query; default values are omitted so the canonical URL stays short.
export function toQuery(state) {
  const out = {}
  if (state.q) out.q = state.q
  if (state.categories?.length) out.cat = state.categories.join(',')
  if (state.tags?.length) out.tags = state.tags.join(',')
  if (state.bbox) out.bbox = state.bbox
  if (state.near) out.near = pointToString(state.near)
  if (state.radius) out.radius = String(state.radius)
  if (state.sort && state.sort !== DEFAULT_STATE.sort) out.sort = state.sort
  if (state.page && state.page !== 1) out.page = String(state.page)
  return out
}

// State -> fetchPlaces params. `fallbackNear` (e.g. the saved lodging) adds distances to the list
// without filtering by radius when the URL has no explicit point.
export function toApiParams(state, { fallbackNear = null } = {}) {
  const point = state.near || fallbackNear
  const params = {}
  if (state.q) params.q = state.q
  if (state.categories?.length) params.category = [...state.categories]
  if (state.tags?.length) params.tags = [...state.tags]
  if (state.bbox) params.bbox = state.bbox
  if (point) params.near = pointToString(point)
  if (state.near && state.radius) params.radius = state.radius
  let sort = state.sort === 'distance' && !point ? 'relevance' : state.sort
  // Without a keyword "relevance" has nothing to rank by; show 진주8경 / 유등 30선 first instead.
  if (sort === 'relevance' && !state.q) sort = 'collection'
  params.sort = sort
  params.page = state.page
  params.size = PAGE_SIZE
  return params
}

// Any filter change goes back to page 1 unless the patch picks a page itself.
export function patchState(state, patch) {
  return { ...state, page: 1, ...patch }
}

// A new keyword search starts from a clean slate but keeps the lodging context (near/radius/sort).
export function searchState(state, q) {
  return { ...DEFAULT_STATE, q: String(q ?? '').trim(), near: state.near, radius: state.radius, sort: state.sort }
}

export function useExploreQuery() {
  const route = useRoute()
  const router = useRouter()
  const state = computed(() => parseQuery(route.query))

  function update(patch, { replace = false } = {}) {
    const query = toQuery(patchState(state.value, patch))
    return router[replace ? 'replace' : 'push']({ name: 'explore', query })
  }

  return { state, update }
}
