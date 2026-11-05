<script setup>
import L, { ATTRIBUTION, MAP_CENTER, MAX_BOUNDS, TILE_DARK, TILE_LIGHT } from './leafletSetup'
import 'leaflet.markercluster'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import './map.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { haversineMeters, boundsToBbox } from '../../utils/geo'
import { formatDistance } from '../../utils/format'
import { buildMarkerOptions, makeClusterIcon, makeMarkerIcon, markerState } from './markerIcons'
import { buildPopup } from './popup'

const props = defineProps({
  markers: { type: Array, default: () => [] },
  savedIds: { type: Set, default: () => new Set() },
  litIds: { type: Set, default: () => new Set() },
  activeId: { type: String, default: null },
  base: { type: Object, default: null },
  radius: { type: Number, default: null },
  fitTo: { type: Array, default: null },
  pickingBase: { type: Boolean, default: false },
  virtualPos: { type: Object, default: null },
  // Pixels at the bottom covered by UI (mobile bottom sheet): fits, bbox and controls avoid it.
  insetBottom: { type: Number, default: 0 },
  dark: { type: Boolean, default: false },
  // id -> href for the popup's "상세 보기" link (router.resolve in the caller).
  detailHref: { type: Function, default: null },
})

const emit = defineEmits(['select', 'moveend', 'pick-base', 'move-virtual', 'toggle-save', 'open'])

const el = ref(null)
let map = null
let tiles = null
let cluster = null
let pinned = null
let baseLayer = null
let virtualMarker = null
let resizeObserver = null
let activeClusterIcon = null
// id -> { marker, data, state, highlighted, group }
const entries = new Map()
// Only moves started by the user (drag, wheel, keys, zoom buttons, cluster clicks) emit `moveend`;
// fits and pans we make ourselves must not pop the "이 지역 재검색" button.
let userGesture = false

// Night map: a dedicated dark tile URL when configured, otherwise a CSS filter on the tile pane.
const tileUrl = (dark) => (dark && TILE_DARK ? TILE_DARK : TILE_LIGHT)
const filterNight = computed(() => props.dark && !TILE_DARK)

const hasCoords = (p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng)
const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

function zIndexFor(state, highlighted) {
  if (highlighted) return 1000
  return state === 'none' ? 0 : 400
}

function popupFor(entry) {
  const { data } = entry
  const distance = props.base ? formatDistance(haversineMeters(props.base, data)) : ''
  return buildPopup(data, {
    distanceText: distance,
    saved: props.savedIds.has(data.id),
    lit: props.litIds.has(data.id),
    href: props.detailHref?.(data.id),
    // Wait for the parent's store update to reach our props, then the popup re-reads it.
    onToggleSave: async (id) => {
      emit('toggle-save', id)
      await nextTick()
    },
    getSaved: (id) => props.savedIds.has(id),
    onOpen: (id) => emit('open', id),
  })
}

function createEntry(data, state, highlighted) {
  const marker = L.marker([data.lat, data.lng], {
    ...buildMarkerOptions(data),
    icon: makeMarkerIcon({ category: data.category, state, highlighted, collection: !!data.is_collection }),
    riseOnHover: true,
    zIndexOffset: zIndexFor(state, highlighted),
    category: data.category,
  })
  const entry = { marker, data, state, highlighted, group: null }
  marker.bindPopup(() => popupFor(entry), {
    className: 'jh-popup',
    minWidth: 220,
    maxWidth: 260,
    autoPanPaddingTopLeft: [20, 70],
    autoPanPaddingBottomRight: [20, 20 + props.insetBottom],
  })
  marker.on('click', () => emit('select', data.id))
  marker.on('keypress', (e) => {
    if (e.originalEvent?.key === 'Enter' || e.originalEvent?.keyCode === 13) emit('select', data.id)
  })
  return entry
}

function groupOf(state) {
  return state === 'none' ? cluster : pinned
}

// Saved/lit markers live outside the clusters so they are always visible. Moving a marker between
// layers closes its popup, so while the popup is open the move waits for `popupclose`.
function placeInGroup(entry) {
  const target = groupOf(entry.state)
  if (entry.group === target) return
  if (entry.marker.isPopupOpen()) {
    entry.marker.once('popupclose', () => setTimeout(() => entries.get(entry.data.id) === entry && placeInGroup(entry)))
    return
  }
  entry.group?.removeLayer(entry.marker)
  target.addLayer(entry.marker)
  entry.group = target
}

function updateEntry(entry, state, highlighted) {
  const { marker, data } = entry
  marker.setIcon(makeMarkerIcon({ category: data.category, state, highlighted, collection: !!data.is_collection }))
  marker.setZIndexOffset(zIndexFor(state, highlighted))
  entry.state = state
  entry.highlighted = highlighted
  placeInGroup(entry)
}

function sync() {
  if (!map) return
  const want = new Map()
  for (const m of props.markers) if (hasCoords(m)) want.set(m.id, m)

  const clusterRemove = []
  for (const [id, entry] of entries) {
    if (want.has(id)) continue
    if (entry.group === cluster) clusterRemove.push(entry.marker)
    else entry.group?.removeLayer(entry.marker)
    entries.delete(id)
  }
  if (clusterRemove.length) cluster.removeLayers(clusterRemove)

  const clusterAdd = []
  for (const data of want.values()) {
    const state = markerState(data.id, props.savedIds, props.litIds)
    const highlighted = data.id === props.activeId
    const entry = entries.get(data.id)
    if (!entry) {
      const created = createEntry(data, state, highlighted)
      entries.set(data.id, created)
      created.group = groupOf(state)
      if (created.group === cluster) clusterAdd.push(created.marker)
      else pinned.addLayer(created.marker)
    } else if (entry.state !== state || entry.highlighted !== highlighted) {
      updateEntry(entry, state, highlighted)
    }
  }
  if (clusterAdd.length) cluster.addLayers(clusterAdd)
  highlightCluster()
}

// When the active place is hidden inside a cluster, light up that cluster instead.
function highlightCluster() {
  activeClusterIcon?.classList.remove('cluster--active')
  activeClusterIcon = null
  const entry = props.activeId && entries.get(props.activeId)
  if (!entry || entry.group !== cluster || !map) return
  const parent = cluster.getVisibleParent(entry.marker)
  if (parent && parent !== entry.marker && parent._icon) {
    activeClusterIcon = parent._icon
    activeClusterIcon.classList.add('cluster--active')
  }
}

function setActive(nextId, prevId) {
  for (const id of [prevId, nextId]) {
    const entry = id && entries.get(id)
    if (entry) updateEntry(entry, entry.state, id === nextId)
  }
  highlightCluster()
}

function labelNode(text) {
  const span = document.createElement('span')
  span.textContent = text
  return span
}

function renderBase() {
  if (!map) return
  baseLayer.clearLayers()
  const b = props.base
  if (!hasCoords(b)) return
  if (props.radius) {
    L.circle([b.lat, b.lng], {
      radius: props.radius,
      color: '#f59e0b',
      weight: 2,
      dashArray: '6 6',
      fillColor: '#fb923c',
      fillOpacity: 0.08,
      interactive: false,
    }).addTo(baseLayer)
  }
  const label = b.label || '기준점'
  const isSameSpot =
    hasCoords(props.virtualPos) &&
    Math.abs(b.lat - props.virtualPos.lat) < 0.0001 &&
    Math.abs(b.lng - props.virtualPos.lng) < 0.0001
  const marker = L.marker([b.lat, b.lng], {
    icon: L.divIcon({
      className: 'jh-base-pin',
      html:
        '<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" focusable="false">' +
        '<circle cx="16" cy="16" r="15" class="base-pin__bg"/>' +
        '<path class="base-pin__house" d="M16 8.5l-7.5 6.2V24h5.2v-5.2h4.6V24h5.2v-9.3z"/></svg>',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }),
    title: `내 숙소 기준점: ${label}`,
    keyboard: false,
    interactive: false,
    zIndexOffset: 1500,
  })
  if (!isSameSpot) {
    marker.bindTooltip(labelNode(label), { permanent: true, direction: 'top', offset: [0, -16], className: 'jh-base-tooltip' })
  }
  marker.addTo(baseLayer)
}

function renderVirtual() {
  if (!map) return
  const pos = props.virtualPos
  if (!hasCoords(pos)) {
    virtualMarker?.remove()
    virtualMarker = null
    return
  }
  if (virtualMarker) {
    virtualMarker.setLatLng([pos.lat, pos.lng])
    return
  }
  virtualMarker = L.marker([pos.lat, pos.lng], {
    draggable: true,
    autoPan: true,
    keyboard: true,
    title: '가상 내 위치 (끌어서 옮기기)',
    zIndexOffset: 2000,
    icon: L.divIcon({
      className: 'jh-virtual-pin',
      html: '<span class="virtual-pin__pulse" aria-hidden="true"></span><span class="virtual-pin__dot" aria-hidden="true"></span>',
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    }),
  })
    .bindTooltip(labelNode('가상 내 위치'), { permanent: true, direction: 'bottom', offset: [0, 12], className: 'jh-virtual-tooltip' })
    .on('dragend', (e) => {
      const { lat, lng } = e.target.getLatLng()
      emit('move-virtual', { lat, lng })
    })
    .addTo(map)
}

// Bounds of the part of the map not covered by the bottom sheet.
function visibleBbox() {
  const size = map.getSize()
  const bottom = Math.max(1, size.y - props.insetBottom)
  const sw = map.containerPointToLatLng([0, bottom])
  const ne = map.containerPointToLatLng([size.x, 0])
  return boundsToBbox(L.latLngBounds(sw, ne))
}

// Center `latlng` in the uncovered part of the map.
function centerOffset(latlng, zoom) {
  if (!props.insetBottom) return latlng
  const point = map.project(latlng, zoom).add([0, props.insetBottom / 2])
  return map.unproject(point, zoom)
}

function applyFit(animate = true) {
  const points = (props.fitTo || []).filter(hasCoords)
  if (!map || !points.length) return
  userGesture = false
  const anim = animate && !reducedMotion()
  if (points.length === 1) {
    const zoom = Math.max(map.getZoom(), 15)
    map.setView(centerOffset(L.latLng(points[0].lat, points[0].lng), zoom), zoom, { animate: anim })
    return
  }
  map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lng])), {
    paddingTopLeft: [40, 70],
    paddingBottomRight: [40, 40 + props.insetBottom],
    maxZoom: 16,
    animate: anim,
  })
}

// Pan/zoom to a marker (revealing it from its cluster) and open its popup.
function focusMarker(id) {
  const entry = entries.get(id)
  if (!map || !entry) return false
  userGesture = false
  const open = () => entry.marker.openPopup()
  if (entry.group === cluster) {
    cluster.zoomToShowLayer(entry.marker, open)
  } else {
    const zoom = Math.max(map.getZoom(), 15)
    map.setView(centerOffset(entry.marker.getLatLng(), zoom), zoom, { animate: !reducedMotion() })
    open()
  }
  return true
}

function closePopup() {
  map?.closePopup()
}

defineExpose({ focusMarker, closePopup })

onMounted(() => {
  map = L.map(el.value, {
    center: MAP_CENTER,
    zoom: 13,
    minZoom: 11,
    maxBounds: MAX_BOUNDS,
    maxBoundsViscosity: 0.8,
    zoomControl: false,
  })
  L.control.zoom({ position: 'topright', zoomInTitle: '확대', zoomOutTitle: '축소' }).addTo(map)
  tiles = L.tileLayer(tileUrl(props.dark), { attribution: ATTRIBUTION, maxZoom: 19 }).addTo(map)

  cluster = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 50,
    chunkedLoading: true,
    iconCreateFunction: (c) => makeClusterIcon(c.getAllChildMarkers().map((m) => m.options.category)),
  }).addTo(map)
  cluster.on('animationend', highlightCluster)
  map.on('zoomend', highlightCluster)
  pinned = L.layerGroup().addTo(map)
  baseLayer = L.layerGroup().addTo(map)

  const container = map.getContainer()
  container.style.setProperty('--map-inset-bottom', `${props.insetBottom}px`)
  for (const type of ['pointerdown', 'wheel', 'keydown', 'touchstart']) {
    container.addEventListener(
      type,
      () => {
        userGesture = true
      },
      { passive: true },
    )
  }
  map.on('moveend', () => {
    if (!userGesture) return
    userGesture = false
    emit('moveend', visibleBbox())
  })
  map.on('click', (e) => {
    if (props.pickingBase) emit('pick-base', { lat: e.latlng.lat, lng: e.latlng.lng })
  })

  if ('ResizeObserver' in window) {
    resizeObserver = new ResizeObserver(() => map?.invalidateSize({ pan: false }))
    resizeObserver.observe(container)
  }

  sync()
  renderBase()
  renderVirtual()
  applyFit(false)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  map?.remove()
  map = null
  entries.clear()
})

watch(() => props.markers, sync)
watch(() => [props.savedIds, props.litIds], sync)
watch(() => props.activeId, setActive)
watch(() => [props.base, props.virtualPos, props.radius], renderBase)
watch(() => props.virtualPos, renderVirtual)
watch(() => props.fitTo, () => applyFit(true))
watch(
  () => props.dark,
  (dark) => {
    if (TILE_DARK) tiles?.setUrl(tileUrl(dark))
  },
)
watch(
  () => props.insetBottom,
  (px) => {
    map?.getContainer().style.setProperty('--map-inset-bottom', `${px}px`)
    for (const { marker } of entries.values()) marker.getPopup().options.autoPanPaddingBottomRight = [20, 20 + px]
  },
)
</script>

<template>
  <!-- Vue owns the wrapper's classes; Leaflet owns the inner element's (never bind :class on it). -->
  <div class="jh-map h-full w-full" :class="{ 'is-picking': pickingBase, 'is-dark': dark, 'tiles-night': filterNight }">
    <div ref="el" class="h-full w-full" role="region" aria-label="진주 장소 지도"></div>
  </div>
</template>
