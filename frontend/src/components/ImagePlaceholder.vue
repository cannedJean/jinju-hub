<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  emoji: { type: String, default: '📍' },
  tintIndex: { type: Number, default: 0 },
})

const imgError = ref(false)

// Reset the error flag if the source changes (e.g. list re-renders with new data).
watch(
  () => props.src,
  () => {
    imgError.value = false
  },
)

function handleError() {
  imgError.value = true
}

const tintClass = computed(() => {
  const classes = ['bg-[#e2edff]', 'bg-[#daf1e7]', 'bg-[#ffecda]', 'bg-[#f2e7ff]']
  return classes[props.tintIndex % classes.length] || classes[0]
})
</script>

<template>
  <div
    class="w-full h-full flex items-center justify-center text-4xl overflow-hidden relative shrink-0"
    :class="tintClass"
  >
    <img
      v-if="src && !imgError"
      :src="src"
      alt=""
      class="w-full h-full object-cover relative z-10"
      @error="handleError"
    />
    <span class="absolute inset-0 flex items-center justify-center z-0" aria-hidden="true">
      {{ emoji }}
    </span>
  </div>
</template>
