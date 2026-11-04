<script setup>
import { CATEGORY_CODES } from '../../composables/useExploreQuery'
import { categoryLabel } from '../../utils/format'

// Multi-select category toggles + the "비 오면 실내" quick filter (tags=indoor).
const props = defineProps({
  categories: { type: Array, default: () => [] },
  tags: { type: Array, default: () => [] },
  counts: { type: Object, default: () => ({}) },
  indoorRecommended: { type: Boolean, default: false },
  // true: wrap onto several lines (side panel); false: one horizontally scrolling row (mobile map).
  wrap: { type: Boolean, default: true },
})
const emit = defineEmits(['update:categories', 'update:tags'])

function toggle(code) {
  const set = new Set(props.categories)
  if (set.has(code)) set.delete(code)
  else set.add(code)
  // Keep the canonical order so URLs stay stable.
  emit(
    'update:categories',
    CATEGORY_CODES.filter((c) => set.has(c)),
  )
}

function toggleTag(tag) {
  const set = new Set(props.tags)
  if (set.has(tag)) set.delete(tag)
  else set.add(tag)
  emit('update:tags', [...set])
}

const indoorOn = () => props.tags.includes('indoor')
</script>

<template>
  <div
    class="chips flex gap-1.5"
    :class="wrap ? 'flex-wrap' : 'flex-nowrap overflow-x-auto chips--scroll'"
    role="group"
    aria-label="카테고리 필터"
  >
    <button
      type="button"
      class="chip"
      :class="{ 'chip--on': categories.length === 0 }"
      :aria-pressed="String(categories.length === 0)"
      @click="emit('update:categories', [])"
    >
      전체
    </button>
    <button
      v-for="code in CATEGORY_CODES"
      :key="code"
      type="button"
      class="chip"
      :class="{ 'chip--on': categories.includes(code) }"
      :aria-pressed="String(categories.includes(code))"
      @click="toggle(code)"
    >
      <span class="chip__dot" :style="{ background: `var(--cat-${code})` }" aria-hidden="true"></span>
      {{ categoryLabel(code) }}
      <span v-if="counts[code]" class="chip__count">{{ counts[code] }}</span>
    </button>

    <span class="chip-divider" aria-hidden="true"></span>

    <button
      type="button"
      class="chip chip--quick"
      :class="{ 'chip--on': indoorOn(), 'chip--recommended': indoorRecommended && !indoorOn() }"
      :aria-pressed="String(indoorOn())"
      :title="indoorRecommended ? '오늘 진주 날씨엔 실내 활동을 추천해요' : '실내에서 즐길 수 있는 곳만 보기'"
      @click="toggleTag('indoor')"
    >
      <span aria-hidden="true">☔</span>
      비 오면 실내
      <span v-if="indoorRecommended" class="chip__badge">오늘 추천</span>
    </button>
  </div>
</template>

<style scoped>
.chip {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--text-body);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.chip:hover {
  border-color: #94a3b8;
}
.chip--on {
  background: var(--color-night-900);
  border-color: var(--color-night-900);
  color: #fff;
}
.chip--on:hover {
  border-color: var(--color-night-900);
}
.chip__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgb(255 255 255 / 0.9);
}
.chip__count {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-muted);
}
.chip--on .chip__count {
  color: rgb(255 255 255 / 0.7);
}
.chip-divider {
  flex: none;
  width: 1px;
  height: 20px;
  margin: 7px 2px;
  background: var(--color-border);
}
.chip--recommended {
  border-color: var(--color-lantern-500);
  background: #fffbeb;
  box-shadow: 0 0 0 3px var(--color-lantern-glow);
}
.chip--quick.chip--on {
  background: var(--color-lantern-500);
  border-color: var(--color-lantern-500);
  color: var(--color-night-900);
}
.chip__badge {
  font-size: 10px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: var(--color-lantern-500);
}
.chips--scroll {
  scrollbar-width: none;
  scroll-snap-type: x proximity;
  padding-bottom: 2px;
}
.chips--scroll::-webkit-scrollbar {
  display: none;
}
.chips--scroll .chip {
  scroll-snap-align: start;
  box-shadow: 0 1px 4px rgb(15 27 61 / 0.15);
}
.chips--scroll .chip--recommended {
  box-shadow: 0 0 0 3px var(--color-lantern-glow);
}
@media (prefers-reduced-motion: reduce) {
  .chip {
    transition: none;
  }
}
</style>
