<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { openDemoSettings } from '../../composables/useDemoSettings'

const TABS = [
  { to: '/', label: '홈', name: '홈', icon: '🏠' },
  { to: '/explore', label: '탐색', icon: '🧭' },
  { to: '/lanterns', label: '내 유등', icon: '🏮' },
  { to: '/festivals', label: '축제', icon: '🎆' },
]
const MORE_LINKS = [
  { to: '/boards', label: '게시판' },
  { to: '/about/data', label: '데이터 출처' },
]

const route = useRoute()
const moreOpen = ref(false)
const moreBtn = ref(null)
const sheet = ref(null)

watch(
  () => route.fullPath,
  () => (moreOpen.value = false),
)
watch(moreOpen, async (open) => {
  if (open) {
    await nextTick()
    sheet.value?.querySelector('a,button')?.focus()
  }
})

function closeMore() {
  moreOpen.value = false
  moreBtn.value?.focus()
}
function openDemo() {
  moreOpen.value = false
  openDemoSettings()
}
</script>

<template>
  <div
    v-if="moreOpen"
    class="fixed inset-0 z-[110] bg-black/40"
    data-test="more-backdrop"
    @click="closeMore"
  ></div>
  <div
    v-if="moreOpen"
    id="more-sheet"
    ref="sheet"
    role="menu"
    aria-label="더보기"
    class="fixed bottom-14 inset-x-0 z-[120] bg-night-900 text-white rounded-t-2xl p-2 shadow-xl"
    @keydown.esc="closeMore"
  >
    <router-link
      v-for="link in MORE_LINKS"
      :key="link.to"
      :to="link.to"
      role="menuitem"
      class="block px-4 py-3 text-[15px] rounded-lg hover:bg-white/10"
    >
      {{ link.label }}
    </router-link>
    <button
      type="button"
      role="menuitem"
      data-test="open-demo"
      class="block w-full text-left px-4 py-3 text-[15px] rounded-lg hover:bg-white/10"
      @click="openDemo"
    >
      시연 설정
    </button>
  </div>

  <nav
    class="fixed bottom-0 inset-x-0 z-[60] h-14 bg-night-900 border-t border-white/10 flex"
    aria-label="하단 메뉴"
  >
    <router-link
      v-for="tab in TABS"
      :key="tab.to"
      :to="tab.to"
      class="flex-1 flex flex-col items-center justify-center text-[12px] text-white/70"
      active-class="text-lantern-500 font-bold"
    >
      <span aria-hidden="true" class="text-[18px] leading-none">{{ tab.icon }}</span>
      {{ tab.label }}
    </router-link>
    <button
      ref="moreBtn"
      type="button"
      data-test="more-tab"
      class="flex-1 flex flex-col items-center justify-center text-[12px]"
      :class="moreOpen ? 'text-lantern-500 font-bold' : 'text-white/70'"
      aria-haspopup="menu"
      :aria-expanded="moreOpen"
      aria-controls="more-sheet"
      @click="moreOpen = !moreOpen"
    >
      <span aria-hidden="true" class="text-[18px] leading-none">☰</span>
      더보기
    </button>
  </nav>
</template>
