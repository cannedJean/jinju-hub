// Single place that prepares Leaflet for the bundler. Import this module *before* any Leaflet plugin:
// plugins such as leaflet.markercluster extend the global `L`, and ES modules evaluate in import order.
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

if (typeof window !== 'undefined' && !window.L) window.L = L

// Fix Leaflet's default marker icons under a bundler (otherwise images 404). From LocalHub PlacesView.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

export const MAP_CENTER = [35.18, 128.108]
// Jinju region bbox (lat 35.05~35.33, lng 127.93~128.30) + 0.05° margin.
export const MAX_BOUNDS = [
  [35.0, 127.88],
  [35.38, 128.35],
]
export const TILE_LIGHT =
  import.meta.env.VITE_TILE_URL || 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
export const TILE_DARK =
  import.meta.env.VITE_TILE_URL_DARK || 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
export const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a> · 한국관광공사 TourAPI · 진주시 공공데이터'

export default L
