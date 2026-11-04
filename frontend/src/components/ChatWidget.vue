<script setup>
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '../stores/chat'
import { useLanternsStore } from '../stores/lanterns'
import { fetchPlace } from '../api/places'
import { toSourceLinks } from '../utils/chatSources'
import { CHAT_SUGGESTIONS as suggestions } from '../data/chatSuggestions'

const chat = useChatStore()
const { history, loading, error, errorMessage } = storeToRefs(chat)

const isOpen = ref(false)
const input = ref('')
const chatBody = ref(null)
const inputElement = ref(null)
const openButton = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

watch(
  () => history.value.length,
  () => scrollToBottom(),
)
watch(loading, () => scrollToBottom())

watch(isOpen, (open) => {
  if (window.matchMedia('(max-width: 767px)').matches) {
    document.body.style.overflow = open ? 'hidden' : ''
  }
  if (open) nextTick(() => inputElement.value?.focus())
})

onUnmounted(() => {
  document.body.style.overflow = ''
})

function closeChat() {
  isOpen.value = false
  nextTick(() => openButton.value?.focus())
}

async function submit(text) {
  const message = String(text ?? '').trim()
  if (!message || loading.value) return
  input.value = ''
  await chat.send(message)
}

// Saves a place source to the lantern list; the summary comes from the place API.
const lanterns = useLanternsStore()
const savingIds = ref(new Set())
const saveFailed = ref(false)

async function saveSource(link) {
  if (savingIds.value.has(link.placeId)) return
  savingIds.value = new Set(savingIds.value).add(link.placeId)
  saveFailed.value = false
  try {
    const place = await fetchPlace(link.placeId)
    lanterns.save({ ...place, id: place.id ?? link.placeId, title: place.title ?? link.label })
  } catch {
    saveFailed.value = true
  } finally {
    const next = new Set(savingIds.value)
    next.delete(link.placeId)
    savingIds.value = next
  }
}
</script>

<template>
  <div
    class="fixed z-[100]"
    :class="isOpen ? 'inset-0 md:inset-auto md:bottom-6 md:right-6' : 'bottom-6 right-6'"
  >
    <div
      v-if="isOpen"
      class="w-full h-full md:w-[400px] md:h-[620px] bg-chat md:rounded-[16px] shadow-2xl flex flex-col md:border border-border overflow-hidden relative z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="chat-title"
      @keydown.esc="closeChat"
    >
      <!-- Header -->
      <div
        class="bg-primary px-4 py-3 md:py-4 flex items-center justify-between text-white shadow-md z-10 shrink-0"
      >
        <div class="flex items-center gap-3">
          <button
            type="button"
            class="md:hidden text-white px-2 py-1 -ml-2 text-xl focus:outline-none"
            aria-label="닫기"
            @click="closeChat"
          >
            ←
          </button>
          <div class="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-xl">
            🤖
          </div>
          <span id="chat-title" class="font-extrabold text-[16px]">진주허브 지역 비서</span>
        </div>
        <button
          type="button"
          class="hidden md:block text-white hover:text-white/80 transition-colors p-2 -mr-2 text-xl focus:outline-none"
          aria-label="닫기"
          @click="closeChat"
        >
          ✕
        </button>
      </div>

      <!-- Body -->
      <div ref="chatBody" class="flex-1 overflow-y-auto p-4 flex flex-col gap-4 relative">
        <div
          v-if="history.length === 0"
          class="absolute inset-0 flex flex-col items-center justify-center text-muted px-6 text-center opacity-70"
        >
          <span class="text-5xl mb-4" aria-hidden="true">💬</span>
          <p class="text-[15px]">
            안녕하세요! 진주 여행 정보를 도와드려요.<br />궁금한 장소나 축제에 대해 물어보세요.
          </p>
        </div>

        <div
          v-for="(msg, idx) in history"
          :key="idx"
          class="flex flex-col max-w-[85%]"
          :class="msg.role === 'user' ? 'self-end' : 'self-start'"
        >
          <div
            class="px-4 py-3 text-[14px] shadow-sm whitespace-pre-wrap leading-relaxed"
            :class="
              msg.role === 'user'
                ? 'bg-primary text-white rounded-l-[12px] rounded-tr-[12px]'
                : 'bg-white text-strong border border-border rounded-r-[12px] rounded-tl-[12px]'
            "
          >
            {{ msg.content }}
          </div>

          <div
            v-if="msg.sources && msg.sources.length"
            class="mt-2 bg-white border border-border rounded-[12px] p-3 shadow-sm text-[13px] self-start w-[260px]"
          >
            <div class="text-primary font-bold mb-2">📍 관련 정보 · 추천 게시글</div>
            <div class="flex flex-col gap-1.5">
              <div
                v-for="(link, sIdx) in toSourceLinks(msg.sources)"
                :key="`${link.kind}-${link.to.params.id}-${sIdx}`"
                class="flex items-center gap-1.5"
              >
                <router-link
                  :to="link.to"
                  class="flex-1 min-w-0 bg-link-chip-bg text-primary px-3 py-2 rounded-[8px] hover:bg-primary-tint text-left transition-colors font-semibold truncate focus:outline-none focus:ring-1 focus:ring-primary"
                  @click="isOpen = false"
                >
                  {{ link.kind === 'post' ? '💬' : '🗺' }} {{ link.label }} ↗
                </router-link>
                <button
                  v-if="link.kind === 'place'"
                  type="button"
                  data-test="source-save"
                  class="shrink-0 border border-primary text-primary px-2 py-1.5 rounded-[8px] text-[12px] font-bold hover:bg-primary-tint disabled:opacity-60 focus:outline-none focus:ring-1 focus:ring-primary"
                  :disabled="lanterns.isSaved(link.placeId) || savingIds.has(link.placeId)"
                  :aria-label="`${link.label} 담기`"
                  @click="saveSource(link)"
                >
                  {{ lanterns.isSaved(link.placeId) ? '담김' : '◇ 담기' }}
                </button>
              </div>
              </div>
          </div>
        </div>

        <div
          v-if="saveFailed"
          class="self-start text-danger text-[13px]"
          role="alert"
        >
          장소 정보를 불러오지 못해 담지 못했어요.
        </div>

        <div
          v-if="loading"
          class="self-start bg-white border border-border rounded-r-[12px] rounded-tl-[12px] px-5 py-3.5 text-[14px] shadow-sm text-muted font-medium"
        >
          <span class="animate-pulse">답변을 작성 중입니다…</span>
        </div>

        <div
          v-if="error"
          class="self-start bg-danger-bg text-danger border border-danger-border rounded-r-[12px] rounded-tl-[12px] px-4 py-3 text-[14px] shadow-sm flex flex-col gap-2"
        >
          <span>{{ errorMessage }}</span>
          <button
            type="button"
            class="self-start bg-white border border-danger px-3 py-1 rounded text-[13px] font-bold hover:bg-page transition-colors focus:outline-none"
            @click="chat.retry()"
          >
            다시 시도
          </button>
        </div>
      </div>

      <!-- Suggestions -->
      <div class="px-4 pb-2 pt-2 flex flex-wrap gap-1.5 shrink-0 bg-chat">
        <button
          v-for="s in suggestions"
          :key="s"
          type="button"
          class="bg-white border border-primary text-primary px-3 py-1.5 rounded-full text-[12px] font-semibold hover:bg-primary-tint transition-colors shadow-sm disabled:opacity-50 whitespace-nowrap focus:outline-none"
          :disabled="loading"
          @click="submit(s)"
        >
          {{ s }}
        </button>
      </div>

      <!-- Input -->
      <div class="p-3 bg-white border-t border-border z-10 shrink-0">
        <div class="relative flex items-center">
          <label for="chat-input" class="sr-only">메시지 입력</label>
          <input
            id="chat-input"
            ref="inputElement"
            v-model="input"
            type="text"
            maxlength="500"
            placeholder="메시지를 입력하세요"
            class="w-full bg-chat border border-border-input rounded-[22px] py-2.5 pl-4 pr-12 outline-none text-[15px] focus:border-primary transition-colors"
            :disabled="loading"
            @keyup.enter="submit(input)"
          />
          <button
            type="button"
            class="absolute right-1 w-9 h-9 bg-primary rounded-full text-white flex items-center justify-center font-bold text-xl hover:bg-primary-strong transition-colors disabled:opacity-50 focus:outline-none"
            :disabled="loading || !input.trim()"
            aria-label="전송"
            @click="submit(input)"
          >
            ↑
          </button>
        </div>
      </div>
    </div>

    <button
      v-if="!isOpen"
      ref="openButton"
      type="button"
      class="w-[64px] h-[64px] bg-primary text-white rounded-full shadow-[0_8px_16px_rgba(37,99,235,0.4)] flex items-center justify-center text-3xl hover:bg-primary-strong transition-all hover:scale-105 active:scale-95 focus:outline-none focus:ring-4 focus:ring-primary-tint"
      aria-label="챗봇 열기"
      @click="isOpen = true"
    >
      💬
    </button>
  </div>
</template>
