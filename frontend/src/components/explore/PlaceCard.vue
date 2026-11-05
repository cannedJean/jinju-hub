<script setup>
import { computed, ref, watch } from 'vue'
import { categoryLabel, formatDistance } from '../../utils/format'

// One result row. Clicking the card shows the place on the map; the title links to the detail page.
const props = defineProps({
  place: { type: Object, required: true },
  active: { type: Boolean, default: false },
  saved: { type: Boolean, default: false },
  lit: { type: Boolean, default: false },
  // Distance in meters when the server did not send one (e.g. map-selected preview).
  distance: { type: Number, default: null },
  isBase: { type: Boolean, default: false },
})
const emit = defineEmits(['hover', 'select', 'toggle-save', 'set-base'])

// Focus moving between the card's own buttons keeps the highlight.
function onFocusOut(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) emit('hover', null)
}

const imgFailed = ref(false)
watch(
  () => props.place.hero_image,
  () => {
    imgFailed.value = false
  },
)

const distanceText = computed(() => formatDistance(props.place.distance_m ?? props.distance))
const badge = computed(() => {
  if (props.place.jinju8_rank) return `진주8경 ${props.place.jinju8_rank}`
  if (props.place.is_collection) return '유등 30선'
  return ''
})
const subtitle = computed(() => props.place.summary || props.place.addr || '')
const canSetBase = computed(
  () => props.place.category === 'stay' && Number.isFinite(props.place.lat) && Number.isFinite(props.place.lng),
)
const hasCoords = computed(() => Number.isFinite(props.place.lat) && Number.isFinite(props.place.lng))
const saveLabel = computed(() => {
  if (props.lit) return `${props.place.title}: 밝힌 곳`
  return props.saved ? `${props.place.title} 담기 취소` : `${props.place.title} 담기`
})
</script>

<template>
  <article
    class="place-card group"
    :class="{ 'place-card--active': active }"
    :data-place-id="place.id"
    @mouseenter="emit('hover', place.id)"
    @mouseleave="emit('hover', null)"
    @focusin="emit('hover', place.id)"
    @focusout="onFocusOut"
    @click="emit('select', place.id)"
  >
    <div class="place-card__thumb" :class="`thumb--${place.category}`">
      <img
        v-if="place.hero_image && !imgFailed"
        :src="place.hero_image"
        alt=""
        loading="lazy"
        decoding="async"
        @error="imgFailed = true"
      />
      <span v-else class="place-card__glyph" aria-hidden="true">{{ categoryLabel(place.category).slice(0, 1) }}</span>
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-1.5 text-[12px] font-bold min-w-0">
        <span class="inline-flex items-center gap-1 whitespace-nowrap" :style="{ color: `var(--cat-${place.category}, #64748b)` }">
          <span class="w-2 h-2 rounded-full" :style="{ background: 'currentColor' }" aria-hidden="true"></span>
          {{ categoryLabel(place.category) }}
        </span>
        <span v-if="badge" class="place-card__badge">◆ {{ badge }}</span>
        <span v-if="distanceText" class="ml-auto whitespace-nowrap text-muted font-semibold">
          <span class="sr-only">기준점에서</span>{{ distanceText }}
        </span>
      </div>

      <h3 class="mt-0.5 text-[15px] font-extrabold text-strong leading-snug truncate">
        <router-link :to="{ name: 'place', params: { id: place.id } }" class="place-card__title" @click.stop>
          {{ place.title }}
        </router-link>
      </h3>
      <p v-if="subtitle" class="text-[13px] text-muted truncate">{{ subtitle }}</p>

      <div v-if="canSetBase" class="mt-1.5">
        <button
          type="button"
          class="place-card__action min-h-[44px]"
          :class="{ 'place-card__action--on': isBase }"
          :disabled="isBase"
          @click.stop="emit('set-base', place)"
        >
          {{ isBase ? '🏠 내 숙소' : '🏠 여기를 숙소로' }}
        </button>
      </div>
    </div>

    <div class="flex-none flex flex-col items-center gap-1.5">
      <button
        type="button"
        class="place-card__icon place-card__save min-h-[44px] min-w-[44px]"
        :class="{ 'is-saved': saved && !lit, 'is-lit': lit }"
        :aria-pressed="lit ? undefined : String(saved)"
        :aria-label="saveLabel"
        :title="lit ? '밝힌 곳' : saved ? '담음 (누르면 취소)' : '갈 만한 곳으로 담기'"
        :disabled="lit"
        @click.stop="emit('toggle-save', place)"
      >
        <span aria-hidden="true">{{ lit ? '◆' : saved ? '◇' : '＋' }}</span>
      </button>
      <button
        v-if="hasCoords"
        type="button"
        class="place-card__icon place-card__map min-h-[44px] min-w-[44px]"
        :aria-label="`${place.title} 지도에서 보기`"
        title="지도에서 보기"
        @click.stop="emit('select', place.id)"
      >
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">
          <path d="M10 1.8a6 6 0 0 0-6 6c0 4.4 6 10.4 6 10.4s6-6 6-10.4a6 6 0 0 0-6-6zm0 8.4a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8z" fill="currentColor" />
        </svg>
      </button>
    </div>
  </article>
</template>

<style scoped>
.place-card {
  position: relative;
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    box-shadow 0.15s;
}
.place-card:hover {
  background: var(--bg-subtle);
}
.place-card--active {
  background: #fffbeb;
  border-color: var(--color-lantern-500);
  box-shadow: 0 0 0 3px var(--color-lantern-glow);
}
.place-card--active:hover {
  background: #fffbeb;
}
.place-card__thumb {
  flex: none;
  width: 76px;
  height: 76px;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-subtle);
}
.place-card__thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.place-card__glyph {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
}
.thumb--sight { background: color-mix(in srgb, var(--cat-sight) 75%, white); }
.thumb--culture { background: color-mix(in srgb, var(--cat-culture) 75%, white); }
.thumb--food { background: color-mix(in srgb, var(--cat-food) 75%, white); }
.thumb--stay { background: color-mix(in srgb, var(--cat-stay) 75%, white); }
.thumb--festival { background: color-mix(in srgb, var(--cat-festival) 75%, white); }
.thumb--shopping { background: color-mix(in srgb, var(--cat-shopping) 75%, white); }
.thumb--leisure { background: color-mix(in srgb, var(--cat-leisure) 75%, white); }
.thumb--course { background: color-mix(in srgb, var(--cat-course) 75%, white); }
.place-card__thumb:has(img) {
  background: var(--bg-subtle);
}
.place-card__badge {
  white-space: nowrap;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: var(--color-lantern-500);
  font-size: 11px;
}
.place-card__title {
  color: inherit;
}
.place-card__title:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.place-card__action {
  min-height: 44px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: 12px;
  font-weight: 700;
  color: var(--text-body);
}
.place-card__action:hover:not(:disabled) {
  border-color: var(--color-night-700);
  color: var(--color-night-900);
}
.place-card__action--on {
  background: var(--color-night-900);
  border-color: var(--color-night-900);
  color: #fff;
}
.place-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: 16px;
  font-weight: 800;
  color: var(--color-muted);
  transition:
    transform 0.15s,
    background-color 0.15s;
}
.place-card__map:hover {
  border-color: var(--color-night-700);
  color: var(--color-night-900);
}
/* The whole card already shows the place on the map; the pin button is the keyboard/explicit path. */
@media (hover: hover) {
  .place-card__map {
    opacity: 0;
    transition: opacity 0.15s;
  }
  .place-card:hover .place-card__map,
  .place-card:focus-within .place-card__map,
  .place-card--active .place-card__map {
    opacity: 1;
  }
}
.place-card__save:hover:not(:disabled) {
  border-color: var(--color-lantern-500);
  color: #b45309;
  transform: scale(1.06);
}
.place-card__save.is-saved {
  background: #fffbeb;
  border-color: var(--color-lantern-500);
  color: #b45309;
}
.place-card__save.is-lit {
  background: var(--color-lantern-500);
  border-color: var(--color-lantern-500);
  color: var(--color-night-900);
  box-shadow: 0 0 10px var(--color-lantern-glow);
  cursor: default;
}
@media (prefers-reduced-motion: reduce) {
  .place-card,
  .place-card__save {
    transition: none;
  }
}
</style>
