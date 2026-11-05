<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { onColdStart } from '../../api/client'

// Free-tier backend sleeps when idle: say so instead of leaving the page looking broken.
const waking = ref(false)
const off = onColdStart((v) => (waking.value = v))
onBeforeUnmount(off)
</script>

<template>
  <div
    v-if="waking"
    data-test="waking-banner"
    class="bg-night-900 text-white text-[13px] font-bold text-center py-1.5 px-4"
    role="status"
  >
    서버를 깨우는 중… 처음 접속하면 최대 2분쯤 걸려요
  </div>
</template>
