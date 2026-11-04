import apiClient from './client'

// Arrays serialize as repeated keys (category=a&category=b).
const paramsSerializer = { indexes: null }

function get(url, params) {
  return apiClient.get(url, { params, paramsSerializer }).then((res) => res.data)
}

export function fetchMeta() {
  return get('/meta')
}

// query: { q, category[], tags[], bbox, near, radius, sort, page, size }
export function fetchPlaces(query = {}) {
  return get('/places', query)
}

export function fetchMarkers() {
  return get('/places/markers')
}

export function fetchPlace(id) {
  return get(`/places/${encodeURIComponent(id)}`)
}

export function fetchCollection() {
  return get('/collection')
}

export function fetchFestivals({ status = 'all', today } = {}) {
  return get('/festivals', { status, today })
}

export function fetchReport() {
  return get('/data/report')
}
