<script setup>
import { nextTick, ref, watch } from 'vue'
import { useLanternsStore, kstToday } from '../../stores/lanterns'
import { closeDemoSettings, demoSettingsOpen } from '../../composables/useDemoSettings'

const FESTIVAL_DATE = '2026-10-10'
const lanterns = useLanternsStore()
const closeBtn = ref(null)
let opener = null

function update(patch) {
  const d = lanterns.demo
  lanterns.setDemo({ enabled: d.enabled, today: d.today, pos: d.pos, ...patch })
}
function toggle(e) {
  const on = e.target.checked
  update({ enabled: on, today: on ? lanterns.demo.today || kstToday() : lanterns.demo.today })
}
function setDate(date) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(date)) update({ enabled: true, today: date })
}

watch(demoSettingsOpen, async (open) => {
  if (open) {
    opener = document.activeElement
    await nextTick()
    closeBtn.value?.focus()
  } else if (opener?.isConnected) {
    opener.focus()
  }
})
</script>

<template>
  <div
    v-if="demoSettingsOpen"
    class="fixed inset-0 z-[90] flex items-end md:items-center justify-center bg-black/50"
    @click.self="closeDemoSettings"
  >
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-settings-title"
      class="w-full md:w-[420px] bg-surface rounded-t-2xl md:rounded-2xl p-5 shadow-xl"
      @keydown.esc="closeDemoSettings"
    >
      <div class="flex items-center justify-between">
        <h2 id="demo-settings-title" class="text-[18px] font-extrabold text-strong">시연 설정</h2>
        <button
          ref="closeBtn"
          type="button"
          class="text-muted text-[14px] px-2 py-1"
          aria-label="시연 설정 닫기"
          @click="closeDemoSettings"
        >
          닫기
        </button>
      </div>

      <label class="mt-4 flex items-center gap-3 text-[15px] text-strong font-medium">
        <input
          type="checkbox"
          data-test="demo-toggle"
          :checked="lanterns.demo.enabled"
          class="w-5 h-5"
          @change="toggle"
        />
        시연 모드
      </label>
      <p class="mt-1 text-[13px] text-muted">기준일을 바꿔 축제 진행 상태와 유등 점등일을 미리 볼 수 있어요.</p>

      <label class="mt-4 block text-[14px] text-strong font-medium">
        기준일
        <input
          type="date"
          data-test="demo-date"
          :value="lanterns.demo.today || ''"
          class="mt-1 block w-full rounded-lg border border-input px-3 py-2 text-[15px]"
          @change="setDate($event.target.value)"
        />
      </label>

      <div class="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          data-test="preset-festival"
          class="px-3 py-2 rounded-full bg-lantern-500 text-night-900 text-[14px] font-bold"
          @click="setDate(FESTIVAL_DATE)"
        >
          유등축제 기간(2026-10-10)
        </button>
        <button
          type="button"
          data-test="preset-today"
          class="px-3 py-2 rounded-full bg-subtle text-strong text-[14px] font-bold"
          @click="setDate(kstToday())"
        >
          오늘
        </button>
      </div>
    </div>
  </div>
</template>
