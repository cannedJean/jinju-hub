const R = 6371008.8

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
