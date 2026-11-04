<script>
export const SNAP_ORDER = ['collapsed', 'half', 'full']
export const SNAP_HEIGHTS = { collapsed: '96px', half: '50vh', full: '90vh' }
</script>

<script setup>
import { computed, ref, useId } from 'vue'

// Mobile list sheet with three snap points. The handle is a real button: click/Enter cycles
// collapsed -> half -> full -> collapsed, ArrowUp/ArrowDown step, and touch/mouse can drag it.
const props = defineProps({
  label: { type: String, default: '장소 목록' },
  summary: { type: String, default: '' },
})
const snap = defineModel('snap', { type: String, default: 'collapsed' })

const bodyId = useId()
const sheetEl = ref(null)
const bodyEl = ref(null)
const dragHeight = ref(null)
let drag = null
let suppressClick = false

const expanded = computed(() => snap.value !== 'collapsed')
const style = computed(() => ({
  height: dragHeight.value !== null ? `${dragHeight.value}px` : SNAP_HEIGHTS[snap.value] || SNAP_HEIGHTS.collapsed,
}))
const nextLabel = computed(() => (snap.value === 'full' ? '목록 접기' : '목록 펼치기'))

function scrollToTop() {
  if (bodyEl.value) bodyEl.value.scrollTop = 0
}
defineExpose({ scrollToTop })

function step(delta) {
  const i = Math.max(0, SNAP_ORDER.indexOf(snap.value))
  snap.value = SNAP_ORDER[Math.min(SNAP_ORDER.length - 1, Math.max(0, i + delta))]
}

function cycle() {
  if (suppressClick) {
    suppressClick = false
    return
  }
  const i = SNAP_ORDER.indexOf(snap.value)
  snap.value = SNAP_ORDER[(i + 1) % SNAP_ORDER.length]
}

function onKeydown(event) {
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    step(1)
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    step(-1)
  } else if (event.key === 'Escape' && snap.value !== 'collapsed') {
    snap.value = 'collapsed'
  }
}

// Snap heights in px for the current viewport (full is capped by the sheet's container).
function snapPx() {
  const vh = window.innerHeight
  const parentH = sheetEl.value?.parentElement?.clientHeight || vh
  return { collapsed: 96, half: vh * 0.5, full: Math.min(vh * 0.9, parentH - 8) }
}

function onPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return
  drag = {
    y: event.clientY,
    h: sheetEl.value?.getBoundingClientRect().height || 96,
    t: performance.now(),
    moved: false,
  }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function onPointerMove(event) {
  if (!drag) return
  const dy = event.clientY - drag.y
  if (!drag.moved && Math.abs(dy) < 6) return
  drag.moved = true
  const px = snapPx()
  dragHeight.value = Math.min(px.full, Math.max(px.collapsed, drag.h - dy))
}

function onPointerUp(event) {
  if (!drag) return
  const d = drag
  drag = null
  if (!d.moved) return
  suppressClick = true
  const h = dragHeight.value
  const velocity = (event.clientY - d.y) / Math.max(1, performance.now() - d.t) // px/ms, + = down
  dragHeight.value = null
  const px = snapPx()
  const entries = SNAP_ORDER.map((name) => [name, px[name]])
  if (velocity < -0.5) {
    snap.value = (entries.find(([, v]) => v > h + 1) || entries.at(-1))[0]
  } else if (velocity > 0.5) {
    snap.value = ([...entries].reverse().find(([, v]) => v < h - 1) || entries[0])[0]
  } else {
    snap.value = entries.reduce((best, cur) => (Math.abs(cur[1] - h) < Math.abs(best[1] - h) ? cur : best))[0]
  }
  // A drag never produces a click on touch screens, so don't swallow the next real one.
  setTimeout(() => {
    suppressClick = false
  }, 0)
}
</script>

<template>
  <section
    ref="sheetEl"
    data-test="sheet"
    class="bottom-sheet"
    :class="{ 'is-dragging': dragHeight !== null }"
    :data-snap="snap"
    :style="style"
    :aria-label="props.label"
  >
    <button
      type="button"
      data-test="sheet-handle"
      class="bottom-sheet__handle"
      :aria-expanded="String(expanded)"
      :aria-controls="bodyId"
      :aria-label="`${nextLabel}${props.summary ? ` (${props.summary})` : ''}`"
      @click="cycle"
      @keydown="onKeydown"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <span class="bottom-sheet__grip" aria-hidden="true"></span>
      <span v-if="props.summary" class="bottom-sheet__summary" aria-hidden="true">{{ props.summary }}</span>
    </button>

    <div class="bottom-sheet__header">
      <slot name="header" />
    </div>

    <div :id="bodyId" ref="bodyEl" class="bottom-sheet__body" :inert="!expanded" :aria-hidden="!expanded ? 'true' : undefined">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.bottom-sheet {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  z-index: 500;
  max-height: calc(100% - 8px);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -8px 30px rgb(15 27 61 / 0.18);
  transition: height 0.28s cubic-bezier(0.2, 0.8, 0.2, 1);
  overflow: hidden;
}
.bottom-sheet.is-dragging {
  transition: none;
}
.bottom-sheet__handle {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 8px 16px 4px;
  touch-action: none;
  cursor: grab;
  background: transparent;
  border: 0;
}
.bottom-sheet__handle:active {
  cursor: grabbing;
}
.bottom-sheet__grip {
  width: 40px;
  height: 5px;
  border-radius: 999px;
  background: #cbd5e1;
}
.bottom-sheet__summary {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-muted);
  line-height: 1;
}
.bottom-sheet__header {
  flex: none;
  padding: 0 12px 8px;
}
.bottom-sheet__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
@media (prefers-reduced-motion: reduce) {
  .bottom-sheet {
    transition: none;
  }
}
</style>
