<script setup>
import L, { ATTRIBUTION, TILE_LIGHT } from '../map/leafletSetup'
import 'leaflet/dist/leaflet.css'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  lat: { type: Number, required: true },
  lng: { type: Number, required: true },
  title: { type: String, default: '' },
})

const el = ref(null)
let map = null
let marker = null

onMounted(() => {
  map = L.map(el.value, { center: [props.lat, props.lng], zoom: 16, scrollWheelZoom: false })
  L.tileLayer(TILE_LIGHT, { attribution: ATTRIBUTION, maxZoom: 19 }).addTo(map)
  marker = L.marker([props.lat, props.lng], { title: props.title }).addTo(map)
})

watch(
  () => [props.lat, props.lng],
  ([lat, lng]) => {
    map?.setView([lat, lng])
    marker?.setLatLng([lat, lng])
  },
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

<template>
  <div ref="el" class="mini-map" role="img" :aria-label="`${title} 위치 지도`"></div>
</template>

<style scoped>
.mini-map {
  height: 220px;
  border-radius: 14px;
  overflow: hidden;
  z-index: 0;
}
</style>
