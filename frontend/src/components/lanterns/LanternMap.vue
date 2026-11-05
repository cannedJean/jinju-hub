<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import MapCanvas from '../map/MapCanvas.vue'

// Map of only the user's own places (markers built from local snapshots).
const props = defineProps({
  items: { type: Array, default: () => [] },
  missing: { type: Object, default: () => new Set() },
})

const router = useRouter()
const usable = computed(() =>
  props.items.filter((it) => !props.missing.has(it.id) && Number.isFinite(it.lat) && Number.isFinite(it.lng)),
)
const markers = computed(() =>
  usable.value.map((it) => ({ id: it.id, title: it.title, category: it.category, lat: it.lat, lng: it.lng, tags: it.tags || [] })),
)
const savedIds = computed(() => new Set(usable.value.map((it) => it.id)))
const litIds = computed(() => new Set(usable.value.filter((it) => it.litAt).map((it) => it.id)))
const fitTo = computed(() => (usable.value.length ? usable.value.map((it) => ({ lat: it.lat, lng: it.lng })) : null))

const detailHref = (id) => router.resolve({ name: 'place', params: { id } }).href
const open = (id) => router.push({ name: 'place', params: { id } })
</script>

<template>
  <div class="lantern-map">
    <MapCanvas
      :markers="markers"
      :saved-ids="savedIds"
      :lit-ids="litIds"
      :fit-to="fitTo"
      :detail-href="detailHref"
      @open="open"
    />
    <p v-if="!markers.length" class="lantern-map__empty">지도에 표시할 장소가 없어요.</p>
  </div>
</template>

<style scoped>
.lantern-map {
  position: relative;
  height: 60vh;
  min-height: 320px;
  border-radius: 14px;
  overflow: hidden;
}
.lantern-map__empty {
  position: absolute;
  inset: auto 0 16px 0;
  text-align: center;
  z-index: 500;
  font-weight: 700;
}
</style>
