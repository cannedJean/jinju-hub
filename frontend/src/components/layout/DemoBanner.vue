<script setup>
defineProps({
  active: { type: Boolean, default: false },
  date: { type: String, default: '' },
})
</script>

<template>
  <div
    v-if="active"
    class="sticky top-0 z-[70] bg-lantern-500 text-night-900 text-[13px] font-bold text-center h-8 leading-8 px-4"
    role="status"
  >
    시연 모드<template v-if="date"> · 기준일 {{ date }}</template>
  </div>
</template>
