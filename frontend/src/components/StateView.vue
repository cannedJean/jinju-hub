<script setup>
defineProps({
  loading: Boolean,
  error: Boolean,
  empty: Boolean,
  errorMessage: { type: String, default: '일시적인 오류가 발생했습니다.' },
  emptyMessage: { type: String, default: '데이터가 없습니다.' },
})

defineEmits(['retry'])
</script>

<template>
  <div v-if="loading" class="flex flex-col justify-center items-center py-16 text-muted gap-4">
    <div class="spinner"></div>
    <span class="text-[14px] font-medium" aria-live="polite">데이터를 불러오는 중입니다...</span>
  </div>

  <div v-else-if="error" class="flex flex-col justify-center items-center py-16 text-center gap-4">
    <span class="text-4xl" aria-hidden="true">⚠️</span>
    <p class="text-[15px] text-strong font-medium" aria-live="assertive">{{ errorMessage }}</p>
    <button
      type="button"
      class="px-5 py-2 bg-subtle text-strong font-bold rounded-lg hover:bg-border transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
      @click="$emit('retry')"
    >
      다시 시도
    </button>
  </div>

  <div v-else-if="empty" class="flex flex-col justify-center items-center py-16 text-center gap-4">
    <span class="text-4xl opacity-50" aria-hidden="true">📭</span>
    <p class="text-[15px] text-muted">{{ emptyMessage }}</p>
  </div>

  <slot v-else></slot>
</template>
