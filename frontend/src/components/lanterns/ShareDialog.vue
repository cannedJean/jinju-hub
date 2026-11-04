<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { encodeShare } from '../../utils/share'

const props = defineProps({ ids: { type: Array, default: () => [] } })
const emit = defineEmits(['close'])

const input = ref(null)
const copied = ref('')
const url = computed(() => `${window.location.origin}/lanterns?share=${encodeShare(props.ids)}`)

onMounted(async () => {
  await nextTick()
  input.value?.focus()
  input.value?.select()
})

async function copy() {
  try {
    await navigator.clipboard.writeText(url.value)
    copied.value = '링크를 복사했어요'
  } catch {
    input.value?.select()
    copied.value = '복사하지 못했어요. 링크를 직접 선택해 복사해 주세요'
  }
}

// Minimal focus trap: Tab cycles inside the dialog.
function onKeydown(e) {
  if (e.key === 'Escape') return emit('close')
  if (e.key !== 'Tab') return
  const f = [...e.currentTarget.querySelectorAll('input,button')]
  if (!f.length) return
  const first = f[0]
  const last = f[f.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}
</script>

<template>
  <div class="share-backdrop" @click.self="emit('close')">
    <div class="share-dialog" role="dialog" aria-modal="true" aria-labelledby="share-title" @keydown="onKeydown">
      <h2 id="share-title" class="text-lg font-extrabold text-strong">내 목록 공유</h2>
      <p class="mt-1 text-[13px] text-muted">이 링크를 받은 사람은 담은 장소 {{ ids.length }}곳을 읽기 전용으로 볼 수 있어요.</p>
      <input ref="input" class="share-input" type="text" readonly :value="url" aria-label="공유 링크" />
      <p v-if="copied" class="text-[13px] text-muted" role="status">{{ copied }}</p>
      <div class="mt-3 flex justify-end gap-2">
        <button type="button" class="share-btn" @click="emit('close')">닫기</button>
        <button type="button" class="share-btn share-btn--primary" @click="copy">링크 복사</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.share-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgb(0 0 0 / 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.share-dialog {
  width: 100%;
  max-width: 440px;
  background: var(--color-surface);
  border-radius: 16px;
  padding: 20px;
}
.share-input {
  margin-top: 12px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 13px;
}
.share-btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-weight: 700;
}
.share-btn--primary {
  background: var(--color-night-900);
  border-color: var(--color-night-900);
  color: #fff;
}
</style>
