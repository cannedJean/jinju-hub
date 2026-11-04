<script setup>
const TABS = [
  { to: '/explore', label: '탐색', icon: '🧭' },
  { to: '/lanterns', label: '내 유등', icon: '🏮' },
  { to: '/festivals', label: '축제', icon: '🎆' },
  { to: '/boards', label: '더보기', icon: '☰' },
]
</script>

<template>
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
  </nav>
</template>
