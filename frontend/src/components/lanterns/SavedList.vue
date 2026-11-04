<script setup>
import PlaceCard from '../explore/PlaceCard.vue'

// Saved places rendered from local snapshots. `missing` ids are tombstones (place no longer served).
const props = defineProps({
  items: { type: Array, default: () => [] },
  missing: { type: Object, default: () => new Set() },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['remove', 'select'])

function remove(it) {
  if (it.litAt && !window.confirm('밝힌 유등 기록도 함께 지워져요. 빼시겠어요?')) return
  emit('remove', it.id)
}
const asPlace = (it) => ({ id: it.id, title: it.title, category: it.category, lat: it.lat, lng: it.lng })
</script>

<template>
  <ul class="flex flex-col gap-2">
    <li v-for="it in items" :key="it.id" class="saved-row" :data-place-id="it.id">
      <div v-if="missing.has(it.id)" class="tomb">
        <div class="min-w-0 flex-1">
          <p class="font-extrabold text-strong truncate">{{ it.title }}</p>
          <p class="text-[13px] text-muted">더 이상 제공되지 않는 장소</p>
        </div>
        <button v-if="!readonly" type="button" class="saved-row__remove" @click="emit('remove', it.id)">
          빼기<span class="sr-only"> {{ it.title }}</span>
        </button>
      </div>
      <template v-else>
        <div class="min-w-0 flex-1">
          <PlaceCard
            :place="asPlace(it)"
            :saved="!readonly"
            :lit="!!it.litAt"
            @select="emit('select', it.id)"
            @toggle-save="!readonly && remove(it)"
          />
        </div>
        <button v-if="!readonly" type="button" class="saved-row__remove" @click="remove(it)">
          빼기<span class="sr-only"> {{ it.title }}</span>
        </button>
      </template>
    </li>
  </ul>
</template>

<style scoped>
.saved-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tomb {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  border: 1px dashed var(--color-border);
  background: var(--bg-subtle);
}
.saved-row__remove {
  flex: none;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: 13px;
  font-weight: 700;
}
.saved-row__remove:hover {
  border-color: #b91c1c;
  color: #b91c1c;
}
</style>
