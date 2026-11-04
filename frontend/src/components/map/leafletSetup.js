// Single place that prepares Leaflet for the bundler. Import this module *before* any Leaflet plugin:
// plugins such as leaflet.markercluster extend the global `L`, and ES modules evaluate in import order.
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { JINJU_MAX_BOUNDS } from '../../utils/geo'

if (typeof window !== 'undefined' && !window.L) window.L = L

// Fix Leaflet's default marker icons under a bundler (otherwise images 404). From LocalHub PlacesView.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

export const MAP_CENTER = [35.18, 128.108]
export const MAX_BOUNDS = JINJU_MAX_BOUNDS
// CARTO raster basemaps now answer with an "API KEY REQUIRED" tile, so OSM is the default.
// Either URL can be replaced via env; without a dark URL the night map is a CSS filter on the tiles.
export const TILE_LIGHT = import.meta.env.VITE_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export const TILE_DARK = import.meta.env.VITE_TILE_URL_DARK || null
export const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors' +
  ' · 한국관광공사 TourAPI · 진주시'

export default L
