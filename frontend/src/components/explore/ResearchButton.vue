<script setup>
// Floating "이 지역 재검색" pill, shown after the user moves the map.
defineProps({
  visible: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['click'])
</script>

<template>
  <Transition name="research">
    <button v-if="visible" type="button" class="research-btn" :disabled="loading" @click="emit('click')">
      <span class="research-btn__icon" :class="{ 'is-spinning': loading }" aria-hidden="true">↻</span>
      이 지역 재검색
    </button>
  </Transition>
</template>

<style scoped>
.research-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  box-shadow:
    0 6px 18px rgb(15 27 61 / 0.35),
    0 0 0 2px rgb(245 158 11 / 0.6);
}
.research-btn:hover {
  background: var(--color-night-700);
}
.research-btn__icon {
  color: var(--color-lantern-500);
  font-size: 16px;
  line-height: 1;
}
.is-spinning {
  animation: research-spin 0.9s linear infinite;
}
@keyframes research-spin {
  to {
    transform: rotate(360deg);
  }
}
.research-enter-active,
.research-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.research-enter-from,
.research-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
@media (prefers-reduced-motion: reduce) {
  .is-spinning {
    animation: none;
  }
  .research-enter-active,
  .research-leave-active {
    transition: none;
  }
}
</style>
