<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})

defineEmits(['update:page'])

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, Math.min(props.page - 2, props.totalPages - 4))
  const end = Math.min(props.totalPages, start + 4)
  for (let i = start; i <= end; i += 1) pages.push(i)
  return pages
})
</script>

<template>
  <nav
    v-if="totalPages > 1"
    class="flex justify-center items-center gap-2 mt-8"
    aria-label="페이지 이동"
  >
    <button
      type="button"
      class="w-9 h-9 flex items-center justify-center rounded-lg border border-border text-strong disabled:opacity-30 hover:bg-page transition-colors focus:outline-none"
      :disabled="page <= 1"
      aria-label="이전 페이지"
      @click="$emit('update:page', page - 1)"
    >
      ‹
    </button>

    <div class="flex gap-1">
      <button
        v-for="p in visiblePages"
        :key="p"
        type="button"
        class="w-9 h-9 flex items-center justify-center rounded-lg transition-colors text-[14px] focus:outline-none"
        :class="p === page ? 'bg-primary text-white font-bold' : 'text-strong hover:bg-page'"
        :aria-current="p === page ? 'page' : undefined"
        @click="$emit('update:page', p)"
      >
        {{ p }}
      </button>
    </div>

    <button
      type="button"
      class="w-9 h-9 flex items-center justify-center rounded-lg border border-border text-strong disabled:opacity-30 hover:bg-page transition-colors focus:outline-none"
      :disabled="page >= totalPages"
      aria-label="다음 페이지"
      @click="$emit('update:page', page + 1)"
    >
      ›
    </button>
  </nav>
</template>
