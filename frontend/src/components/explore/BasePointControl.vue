<script setup>
import { RADII } from '../../composables/useExploreQuery'
import { formatRadius } from '../../utils/format'

// "내 숙소 설정": pick on the map / use current location (stay cards offer "여기를 숙소로"),
// then choose a radius. The parent turns this into near/radius/sort=distance in the URL.
defineProps({
  base: { type: Object, default: null }, // { lat, lng, label } currently shown on the map
  radius: { type: Number, default: null }, // active radius filter (null = off)
  picking: { type: Boolean, default: false },
  locating: { type: Boolean, default: false },
  message: { type: String, default: '' },
})
const emit = defineEmits(['pick', 'cancel-pick', 'locate', 'update:radius', 'clear'])
</script>

<template>
  <div class="base-control">
    <div v-if="picking" class="flex items-center gap-2" role="status">
      <span class="base-control__icon is-pulsing" aria-hidden="true">📍</span>
      <p class="flex-1 text-[13px] font-bold text-strong">지도를 눌러 숙소 위치를 골라 주세요.</p>
      <button type="button" class="base-btn" @click="emit('cancel-pick')">취소</button>
    </div>

    <template v-else-if="!base">
      <div class="flex items-start gap-2.5">
        <span class="base-control__icon" aria-hidden="true">🏠</span>
        <div class="min-w-0 flex-1">
          <p class="text-[14px] font-extrabold text-strong">내 숙소 기준으로 보기</p>
          <p class="text-[12px] text-muted leading-snug">숙소를 정하면 반경 안 장소를 가까운 순으로 보여 드려요.</p>
        </div>
      </div>
      <div class="mt-2 grid grid-cols-2 gap-1.5">
        <button type="button" class="base-btn" @click="emit('pick')">지도에서 찍기</button>
        <button type="button" class="base-btn" :disabled="locating" @click="emit('locate')">
          {{ locating ? '위치 확인 중…' : '현재 위치' }}
        </button>
      </div>
      <p class="mt-1.5 text-[11px] text-faint">숙박 목록의 ‘여기를 숙소로’로도 정할 수 있어요.</p>
    </template>

    <template v-else>
      <div class="flex items-center gap-2">
        <span class="base-control__icon" aria-hidden="true">🏠</span>
        <div class="min-w-0 flex-1">
          <p class="text-[11px] font-bold text-muted leading-none">내 숙소</p>
          <p class="text-[14px] font-extrabold text-strong truncate">{{ base.label || '기준점' }}</p>
        </div>
        <button type="button" class="base-btn base-btn--ghost" @click="emit('pick')">변경</button>
        <button type="button" class="base-btn base-btn--ghost" aria-label="숙소 기준점 해제" @click="emit('clear')">✕</button>
      </div>
      <div class="mt-2 flex items-center gap-1" role="group" aria-label="숙소 반경">
        <button
          v-for="r in RADII"
          :key="r"
          type="button"
          class="radius-btn"
          :class="{ 'radius-btn--on': radius === r }"
          :aria-pressed="String(radius === r)"
          @click="emit('update:radius', radius === r ? null : r)"
        >
          {{ formatRadius(r) }}
        </button>
        <button
          type="button"
          class="radius-btn"
          :class="{ 'radius-btn--on': !radius }"
          :aria-pressed="String(!radius)"
          @click="emit('update:radius', null)"
        >
          전체
        </button>
      </div>
    </template>

    <p v-if="message" class="mt-1.5 text-[12px] font-semibold text-danger" role="status">{{ message }}</p>
  </div>
</template>

<style scoped>
.base-control {
  padding: 10px 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, #fffbeb 0%, #fff7ed 100%);
  border: 1px solid #fde7c3;
}
.base-control__icon {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-night-900);
  font-size: 15px;
}
.is-pulsing {
  animation: base-pulse 1.4s ease-in-out infinite;
}
@keyframes base-pulse {
  50% {
    box-shadow: 0 0 0 6px var(--color-lantern-glow);
  }
}
.base-btn {
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  background: var(--color-night-900);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.base-btn:disabled {
  opacity: 0.6;
}
.base-btn--ghost {
  background: transparent;
  color: var(--color-night-700);
  border: 1px solid #f3d9a8;
}
.base-btn--ghost:hover {
  background: #fff;
}
.radius-btn {
  flex: 1;
  height: 30px;
  border-radius: 8px;
  border: 1px solid #f3d9a8;
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-body);
}
.radius-btn--on {
  background: var(--color-lantern-500);
  border-color: var(--color-lantern-500);
  color: var(--color-night-900);
}
@media (prefers-reduced-motion: reduce) {
  .is-pulsing {
    animation: none;
  }
}
</style>
