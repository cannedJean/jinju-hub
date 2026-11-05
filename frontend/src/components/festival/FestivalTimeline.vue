<script setup>
import { computed } from 'vue'

const props = defineProps({
  festivals: { type: Array, default: () => [] },
  today: { type: String, default: '' },
})

const year = computed(() => Number(String(props.today).slice(0, 4)) || new Date().getFullYear())
const MONTHS = Array.from({ length: 12 }, (_, i) => `${i + 1}월`)
const DAY = 86400000
const yearStart = computed(() => Date.UTC(year.value, 0, 1))
const yearDays = computed(() => (Date.UTC(year.value + 1, 0, 1) - yearStart.value) / DAY)

function ts(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s ?? ''))
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : null
}

// Bars clipped to this year; open-ended festivals draw a single-day marker.
const bars = computed(() =>
  props.festivals
    .map((f) => {
      const s = ts(f.start_date)
      if (s === null) return null
      const e = ts(f.end_date) ?? s
      const a = Math.max(s, yearStart.value)
      const b = Math.min(e, yearStart.value + (yearDays.value - 1) * DAY)
      if (b < a) return null
      const left = ((a - yearStart.value) / DAY / yearDays.value) * 100
      const width = Math.max((((b - a) / DAY + 1) / yearDays.value) * 100, 1)
      return { id: f.id, title: f.title, status: f.status, left, width }
    })
    .filter(Boolean),
)
const todayPct = computed(() => {
  const t = ts(props.today)
  if (t === null || t < yearStart.value) return null
  const d = (t - yearStart.value) / DAY
  return d < yearDays.value ? (d / yearDays.value) * 100 : null
})
</script>

<template>
  <section aria-label="올해 축제 일정" class="bg-card border border-border rounded-xl p-4">
    <h2 class="text-[15px] font-extrabold text-strong mb-3">{{ year }}년 축제 일정</h2>
    <div class="overflow-x-auto pb-2">
      <div class="relative min-w-[640px]">
        <div class="grid grid-cols-12 text-[11px] text-muted text-center border-b border-border pb-1">
          <span v-for="m in MONTHS" :key="m">{{ m }}</span>
        </div>
        <div
          v-if="todayPct !== null"
          class="absolute top-0 bottom-0 w-px bg-danger"
          :style="{ left: todayPct + '%' }"
          aria-hidden="true"
        ></div>
        <ul class="mt-2 space-y-1.5">
          <li v-for="b in bars" :key="b.id" class="relative h-6" data-test="timeline-bar">
            <span
              class="absolute top-0 h-6 rounded-full text-[11px] leading-6 px-2 truncate font-bold"
              :class="b.status === 'ongoing' ? 'bg-lantern-500 text-night-900' : 'bg-primary-tint text-primary-strong border border-selected-border'"
              :style="{ left: b.left + '%', width: b.width + '%', minWidth: '4rem' }"
              :title="b.title"
            >
              {{ b.title }}
            </span>
          </li>
        </ul>
        <p v-if="!bars.length" class="text-[13px] text-muted py-2">올해 일정이 확정된 축제가 없어요.</p>
      </div>
    </div>
  </section>
</template>
