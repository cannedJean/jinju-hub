<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useCollectionStore } from '../../stores/collection'
import { useLanternsStore } from '../../stores/lanterns'

// Rendered once globally. Consumes collection.newlyEarned (badge modal) and announces the first light.
const collection = useCollectionStore()
const lanterns = useLanternsStore()

const toast = ref('')
const queue = ref([])
const closeBtn = ref(null)
let timer = null
let opener = null

function showToast(text) {
  toast.value = text
  clearTimeout(timer)
  timer = setTimeout(() => (toast.value = ''), 4500)
}
onBeforeUnmount(() => clearTimeout(timer))

watch(
  () => lanterns.litCount,
  (n, prev) => {
    if (n === 1 && prev === 0) showToast('첫 유등을 밝혔어요!')
  },
)

watch(
  () => collection.newlyEarned.length,
  async (n) => {
    if (!n) return
    // The first-light badge is already celebrated by the toast above.
    if (!queue.value.length) opener = document.activeElement
    queue.value.push(...collection.consumeNewlyEarned().filter((b) => b.id !== 'first_light'))
    await nextTick()
    closeBtn.value?.focus()
  },
)

async function close() {
  queue.value.shift()
  await nextTick()
  if (queue.value.length) closeBtn.value?.focus()
  else if (opener?.isConnected) opener.focus()
}

// One focusable control only: keep focus on it.
function onKeydown(e) {
  if (e.key === 'Escape') close()
  else if (e.key === 'Tab') {
    e.preventDefault()
    closeBtn.value?.focus()
  }
}
</script>

<template>
  <div>
    <div class="sr-only" role="status" aria-live="polite">{{ toast }}</div>
    <div v-if="toast" class="toast" aria-hidden="true"><span class="toast__lantern">◆</span>{{ toast }}</div>

    <div v-if="queue.length" class="modal-backdrop">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="badge-title" @keydown="onKeydown">
        <div class="modal__lantern" aria-hidden="true">◆</div>
        <p class="text-[13px] font-bold text-muted">배지를 획득했어요</p>
        <h2 id="badge-title" class="text-xl font-extrabold text-strong">{{ queue[0].label }}</h2>
        <p v-if="queue[0].description" class="mt-1 text-[14px] text-muted">{{ queue[0].description }}</p>
        <button ref="closeBtn" type="button" class="modal__btn" @click="close">닫기</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toast {
  position: fixed;
  left: 50%;
  bottom: 88px;
  transform: translateX(-50%);
  z-index: 300;
  /* left: 50% would cap the shrink-to-fit width at half the viewport and wrap the text. */
  width: max-content;
  max-width: calc(100vw - 32px);
  padding: 12px 20px;
  border-radius: 999px;
  background: var(--color-night-900);
  color: #fff;
  font-weight: 800;
  box-shadow: 0 6px 20px rgb(0 0 0 / 0.3);
}
.toast__lantern {
  margin-right: 8px;
  color: var(--color-lantern-500);
  display: inline-block;
  animation: float-up 1.6s ease-out;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgb(0 0 0 / 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal {
  width: 100%;
  max-width: 360px;
  padding: 28px 20px 20px;
  border-radius: 20px;
  text-align: center;
  background: var(--color-surface);
}
.modal__lantern {
  font-size: 44px;
  line-height: 1;
  color: var(--color-lantern-500);
  text-shadow: 0 0 18px var(--color-lantern-glow);
  animation: float-up 2.4s ease-out;
}
.modal__btn {
  margin-top: 18px;
  min-height: 44px;
  padding: 0 28px;
  border-radius: 12px;
  background: var(--color-night-900);
  color: #fff;
  font-weight: 800;
}
@keyframes float-up {
  from {
    transform: translateY(24px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
/* Mobile: clear the tab bar and the chat bubble above it (ChatWidget bottom 72px + 64px). */
@media (max-width: 767px) {
  .toast {
    bottom: 148px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .toast__lantern,
  .modal__lantern {
    animation: none;
  }
}
</style>
