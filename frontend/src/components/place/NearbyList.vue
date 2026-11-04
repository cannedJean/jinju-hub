<script setup>
import PlaceCard from '../explore/PlaceCard.vue'
import { useLanternsStore } from '../../stores/lanterns'

defineProps({ items: { type: Array, default: () => [] } })
const lanterns = useLanternsStore()

function toggle(place) {
  if (lanterns.isLit(place.id)) return
  if (lanterns.isSaved(place.id)) lanterns.unsave(place.id)
  else lanterns.save(place)
}
</script>

<template>
  <ul v-if="items.length" class="flex flex-col">
    <li v-for="p in items" :key="p.id">
      <PlaceCard
        :place="p"
        :saved="lanterns.isSaved(p.id)"
        :lit="lanterns.isLit(p.id)"
        @toggle-save="toggle"
      />
    </li>
  </ul>
</template>
