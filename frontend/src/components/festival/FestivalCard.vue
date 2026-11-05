<script setup>
import { computed } from 'vue'
import ImagePlaceholder from '../ImagePlaceholder.vue'
import { formatDateRange } from '../../utils/format'
import { useMarkersStore } from '../../stores/markers'

const props = defineProps({ festival: { type: Object, required: true } })
const markersStore = useMarkersStore()

const range = computed(() => formatDateRange(props.festival.start_date, props.festival.end_date) || '일정 미정')
const CHIP = {
  ongoing: 'bg-lantern-500 text-night-900',
  upcoming: 'bg-primary-tint text-primary-strong',
}

function placeTitle(id, index) {
  const marker = markersStore.byId?.get(id) || markersStore.items?.find?.((m) => m.id === id)
  if (marker?.title) return marker.title
  if (Array.isArray(props.festival.place_titles) && props.festival.place_titles[index]) {
    return props.festival.place_titles[index]
  }
  if (props.festival.place_title) return props.festival.place_title
  if (props.festival.place?.title) return props.festival.place?.title
  if (props.festival.location) return props.festival.location
  return props.festival.venue_place_ids?.length > 1 ? `행사 장소 ${index + 1}` : '진주시 일원'
}
</script>

<template>
  <article class="bg-card rounded-xl border border-border overflow-hidden flex flex-col" data-test="festival-card">
    <div class="h-40 bg-subtle">
      <img
        v-if="festival.hero_image"
        :src="festival.hero_image"
        alt=""
        loading="lazy"
        class="w-full h-full object-contain"
      />
      <ImagePlaceholder v-else emoji="🎆" />
    </div>
    <p v-if="festival.hero_image" class="px-4 pt-1 text-[11px] text-muted">사진: 한국관광공사·진주시 제공</p>
    <div class="p-4 flex-1 flex flex-col gap-2">
      <div class="flex items-center gap-2 flex-wrap">
        <span
          class="text-[12px] font-bold px-2 py-0.5 rounded-full"
          :class="CHIP[festival.status] || 'bg-subtle text-muted'"
          data-test="status-chip"
        >
          {{ festival.status_label }}
        </span>
        <span v-if="range && range !== festival.status_label" class="text-[13px] text-muted">{{ range }}</span>
      </div>
      <h3 class="text-[17px] font-extrabold text-strong">{{ festival.title }}</h3>
      <p v-if="festival.summary" class="text-[14px] text-body">{{ festival.summary }}</p>
      <ul v-if="festival.programs?.length" class="text-[13px] text-body list-disc pl-5">
        <li v-for="(p, i) in festival.programs" :key="i">{{ typeof p === 'string' ? p : p.title || p.name }}</li>
      </ul>
      <p v-if="festival.addr" class="text-[13px] text-muted">{{ festival.addr }}</p>
      <div v-if="festival.venue_place_ids?.length" class="flex flex-wrap gap-2 mt-auto pt-1">
        <router-link
          v-for="(id, i) in festival.venue_place_ids"
          :key="id"
          :to="`/places/${id}`"
          class="text-[13px] font-bold text-primary underline underline-offset-2"
        >
          {{ placeTitle(id, i) }}
        </router-link>
      </div>
    </div>
  </article>
</template>
