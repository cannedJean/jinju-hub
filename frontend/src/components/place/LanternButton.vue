<script setup>
import { computed } from 'vue'
import { useLanternsStore } from '../../stores/lanterns'

const props = defineProps({ place: { type: Object, required: true } })
const lanterns = useLanternsStore()

const lit = computed(() => lanterns.isLit(props.place.id))
const saved = computed(() => lanterns.isSaved(props.place.id))
const label = computed(() => (lit.value ? '◆ 밝힘' : saved.value ? '◇ 담음 · 빼기' : '◇ 유등 띄우기(담기)'))

function toggle() {
  if (lit.value) return
  if (saved.value) lanterns.unsave(props.place.id)
  else lanterns.save(props.place)
}
</script>

<template>
  <button
    type="button"
    class="lantern-btn"
    :class="{ 'is-saved': saved && !lit, 'is-lit': lit }"
    :disabled="lit"
    :aria-pressed="lit ? undefined : String(saved)"
    @click="toggle"
  >
    {{ label }}
  </button>
</template>

<style scoped>
.lantern-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-weight: 800;
  font-size: 14px;
}
.lantern-btn.is-saved {
  background: #fffbeb;
  border-color: var(--color-lantern-500);
  color: #b45309;
}
.lantern-btn.is-lit {
  background: var(--color-lantern-500);
  border-color: var(--color-lantern-500);
  color: var(--color-night-900);
  cursor: default;
}
</style>
