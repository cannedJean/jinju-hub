<script setup>
import { nextTick, ref, watch } from 'vue'
import PlaceCard from './PlaceCard.vue'
import Pagination from '../Pagination.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  totalPages: { type: Number, default: 0 },
  activeId: { type: String, default: null },
  selectedId: { type: String, default: null },
  savedIds: { type: Set, default: () => new Set() },
  litIds: { type: Set, default: () => new Set() },
  // Marker picked on the map that is not on the current page: shown pinned above the list.
  preview: { type: Object, default: null },
  previewDistance: { type: Number, default: null },
  // Current lodging point: the matching stay card shows '내 숙소'.
  basePoint: { type: Object, default: null },
  hasFilters: { type: Boolean, default: false },
})
const emit = defineEmits(['hover', 'select', 'toggle-save', 'set-base', 'update:page', 'retry', 'reset'])

const root = ref(null)

const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

// Map selection -> bring the matching card into view.
watch(
  () => props.selectedId,
  async (id) => {
    if (!id) return
    await nextTick()
    const node = [...(root.value?.querySelectorAll('[data-place-id]') || [])].find((n) => n.dataset.placeId === id)
    node?.scrollIntoView?.({ block: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
  },
)

const isBase = (place) =>
  !!props.basePoint &&
  place.category === 'stay' &&
  Math.abs(place.lat - props.basePoint.lat) < 1e-5 &&
  Math.abs(place.lng - props.basePoint.lng) < 1e-5
</script>

<template>
  <div ref="root" class="place-list">
    <div v-if="preview" class="px-2 pt-2">
      <p class="px-2 pb-1 text-[12px] font-bold text-muted">지도에서 고른 장소</p>
      <PlaceCard
        :place="preview"
        :active="true"
        :saved="savedIds.has(preview.id)"
        :lit="litIds.has(preview.id)"
        :distance="previewDistance"
        :is-base="isBase(preview)"
        @select="emit('select', $event)"
        @toggle-save="emit('toggle-save', $event)"
        @set-base="emit('set-base', $event)"
      />
      <hr class="mx-2 mt-2 border-border" />
    </div>

    <!-- First load: skeleton rows -->
    <ul v-if="loading && !items.length" class="p-2 space-y-1" aria-busy="true" aria-label="장소 불러오는 중">
      <li v-for="n in 6" :key="n" class="flex gap-3 p-3">
        <div class="skeleton w-[76px] h-[76px] rounded-xl"></div>
        <div class="flex-1 space-y-2 py-1">
          <div class="skeleton h-3 w-16 rounded"></div>
          <div class="skeleton h-4 w-3/4 rounded"></div>
          <div class="skeleton h-3 w-1/2 rounded"></div>
        </div>
      </li>
    </ul>

    <div v-else-if="error && !items.length" class="px-6 py-12 text-center">
      <p class="text-[15px] font-bold text-strong">목록을 불러오지 못했어요.</p>
      <p class="mt-1 text-[13px] text-muted">네트워크 상태를 확인한 뒤 다시 시도해 주세요.</p>
      <button type="button" class="list-btn mt-4" @click="emit('retry')">다시 시도</button>
    </div>

    <div v-else-if="!items.length" class="px-6 py-12 text-center">
      <p class="text-3xl" aria-hidden="true">🏮</p>
      <p class="mt-2 text-[15px] font-bold text-strong">조건에 맞는 장소가 없어요.</p>
      <p class="mt-1 text-[13px] text-muted leading-relaxed">
        카테고리를 줄이거나, 반경을 넓히거나,<br />지도를 옮겨 ‘이 지역 재검색’을 눌러 보세요.
      </p>
      <button v-if="hasFilters" type="button" class="list-btn mt-4" @click="emit('reset')">필터 모두 지우기</button>
    </div>

    <template v-else>
      <div v-if="error" class="mx-3 mt-2 rounded-lg bg-danger-bg border border-danger-border px-3 py-2 text-[13px] text-danger flex items-center gap-2" role="alert">
        새 목록을 불러오지 못했어요.
        <button type="button" class="ml-auto font-bold underline underline-offset-2" @click="emit('retry')">재시도</button>
      </div>
      <ul class="p-2 space-y-0.5 transition-opacity" :class="{ 'opacity-50 pointer-events-none': loading }" :aria-busy="loading ? 'true' : 'false'">
        <li v-for="place in items" :key="place.id">
          <PlaceCard
            :place="place"
            :active="place.id === activeId || place.id === selectedId"
            :saved="savedIds.has(place.id)"
            :lit="litIds.has(place.id)"
            :is-base="isBase(place)"
            @hover="emit('hover', $event)"
            @select="emit('select', $event)"
            @toggle-save="emit('toggle-save', $event)"
            @set-base="emit('set-base', $event)"
          />
        </li>
      </ul>
      <div class="pb-4">
        <Pagination :page="page" :total-pages="totalPages" @update:page="emit('update:page', $event)" />
      </div>
      <p class="px-5 pb-5 text-[11px] text-faint">이미지 · 정보 출처: 한국관광공사 TourAPI · 진주시 공공데이터</p>
    </template>
  </div>
</template>

<style scoped>
.skeleton {
  background: linear-gradient(90deg, #eef2f7 25%, #f8fafc 50%, #eef2f7 75%);
  background-size: 200% 100%;
  animation: skeleton 1.2s ease-in-out infinite;
}
@keyframes skeleton {
  from {
    background-position: 200% 0;
  }
  to {
    background-position: -200% 0;
  }
}
.list-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 10px;
  background: var(--color-night-900);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>
