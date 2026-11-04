<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StateView from '../components/StateView.vue'
import { fetchPost, deletePost } from '../api/posts'
import { getApiDetail, getApiStatus } from '../api/client'
import { usePostAuthStore } from '../stores/postAuth'
import { getCategoryColor, getCategoryLabel, formatDate } from '../utils/constants'

const route = useRoute()
const router = useRouter()
const authStore = usePostAuthStore()

const post = ref(null)
const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')
const notFound = ref(false)

const modalOpen = ref(false)
const modalAction = ref('')
const pwd = ref('')
const pwdError = ref('')
const isSubmitting = ref(false)
const pwdInput = ref(null)
const dialogRef = ref(null)
let previouslyFocused = null

async function loadData() {
  loading.value = true
  error.value = false
  errorMessage.value = ''
  notFound.value = false
  try {
    post.value = await fetchPost(route.params.id)
  } catch (e) {
    post.value = null
    if (getApiStatus(e) === 404) {
      notFound.value = true
    } else {
      error.value = true
      errorMessage.value = getApiDetail(e, '게시글을 불러올 수 없습니다.')
    }
  } finally {
    loading.value = false
  }
}

function openModal(action) {
  previouslyFocused = document.activeElement
  modalAction.value = action
  pwd.value = ''
  pwdError.value = ''
  modalOpen.value = true
  document.body.style.overflow = 'hidden'
  nextTick(() => pwdInput.value?.focus())
}

function hideModal() {
  modalOpen.value = false
  document.body.style.overflow = ''
  nextTick(() => previouslyFocused?.focus?.())
}

function closeModal() {
  if (isSubmitting.value) return
  hideModal()
}

function handleModalKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeModal()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = Array.from(
    dialogRef.value?.querySelectorAll('input:not([disabled]), button:not([disabled])') || [],
  )
  if (focusable.length === 0) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

async function confirmAction() {
  if (isSubmitting.value) return
  if (!pwd.value || pwd.value.length < 4) {
    pwdError.value = '비밀번호를 4자 이상 입력해 주세요.'
    return
  }

  if (modalAction.value === 'edit') {
    // Carry the password in memory; PUT on the edit form performs the real verification.
    authStore.remember(route.params.id, pwd.value)
    hideModal()
    router.push(`/boards/${route.params.id}/edit`)
    return
  }

  // delete
  isSubmitting.value = true
  pwdError.value = ''
  try {
    await deletePost(route.params.id, pwd.value)
    hideModal()
    router.push('/boards')
  } catch (e) {
    const status = getApiStatus(e)
    if (status === 403) {
      pwdError.value = '비밀번호가 일치하지 않습니다.'
    } else if (status === 404) {
      pwdError.value = '이미 삭제되었거나 존재하지 않는 게시글입니다.'
    } else {
      pwdError.value = getApiDetail(e, '삭제에 실패했습니다. 다시 시도해 주세요.')
    }
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadData)
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="max-w-[800px] mx-auto px-6 py-8 min-h-[calc(100vh-260px)] relative">
    <button
      type="button"
      class="text-muted text-[15px] font-medium hover:text-primary mb-6 flex items-center gap-1 focus:outline-none"
      @click="router.push('/boards')"
    >
      ‹ 목록으로
    </button>

    <div v-if="notFound" class="bg-white rounded-[14px] border border-border p-10 text-center shadow-sm">
      <div class="text-[48px] font-extrabold text-primary mb-2">404</div>
      <h1 class="text-[22px] font-extrabold text-heading mb-3">존재하지 않는 게시글입니다.</h1>
      <p class="text-[15px] text-muted mb-6">삭제되었거나 잘못된 게시글 주소입니다.</p>
      <router-link
        to="/boards"
        class="inline-flex px-5 py-2.5 bg-primary text-white font-bold rounded-[10px] hover:bg-primary-strong"
      >
        게시판으로 돌아가기
      </router-link>
    </div>

    <StateView v-else :loading="loading" :error="error" :error-message="errorMessage" @retry="loadData">
      <div v-if="post" class="bg-white rounded-[14px] border border-border p-6 md:p-10 shadow-sm">
        <span :class="['cat-badge', getCategoryColor(post.category)]">
          {{ getCategoryLabel(post.category) }}
        </span>
        <h1 class="text-[24px] font-extrabold text-heading mt-4 mb-5 leading-tight">
          {{ post.title }}
        </h1>

        <div class="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-border gap-4">
          <div class="text-[13px] text-faint font-medium">
            작성일 {{ formatDate(post.created_at) }}
            <span v-if="post.views !== undefined && post.views !== null"> · 조회 {{ post.views }}</span>
            <span v-if="post.updated_at"> · 수정됨 {{ formatDate(post.updated_at) }}</span>
          </div>
          <div class="flex gap-2 shrink-0">
            <button
              type="button"
              class="px-4 py-1.5 border border-selected-border text-primary text-[14px] font-bold rounded-lg hover:bg-primary-tint transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
              @click="openModal('edit')"
            >
              수정
            </button>
            <button
              type="button"
              class="px-4 py-1.5 bg-danger-bg border border-danger-border text-danger text-[14px] font-bold rounded-lg hover:brightness-95 transition-all focus:outline-none focus:ring-2 focus:ring-danger"
              @click="openModal('delete')"
            >
              삭제
            </button>
          </div>
        </div>

        <div class="py-8 text-[16px] text-body whitespace-pre-wrap leading-[1.6]">
          {{ post.content }}
        </div>
      </div>
    </StateView>

    <!-- Password confirm modal -->
    <div
      v-if="modalOpen"
      class="fixed inset-0 bg-[#111827]/55 flex items-center justify-center z-[100] p-6"
      @click.self="closeModal"
      @keydown="handleModalKeydown"
    >
      <div
        ref="dialogRef"
        class="bg-white w-full max-w-[420px] rounded-[16px] shadow-2xl p-7"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pw-modal-title"
        aria-describedby="pw-modal-description"
      >
        <h3 id="pw-modal-title" class="text-[20px] font-bold text-heading mb-2">비밀번호 확인</h3>
        <p id="pw-modal-description" class="text-[14px] text-muted mb-5 leading-relaxed">
          게시글 작성 시 입력한 비밀번호를 입력해 주세요.
        </p>

        <label for="modal-pwd" class="sr-only">비밀번호</label>
        <input
          id="modal-pwd"
          ref="pwdInput"
          v-model="pwd"
          type="password"
          placeholder="••••••"
          class="w-full h-[48px] bg-page border border-border-input rounded-[10px] px-4 outline-none focus:border-primary focus:ring-1 focus:ring-primary text-center text-lg tracking-[0.3em]"
          @keyup.enter="confirmAction"
        />
        <p v-if="pwdError" class="text-[13px] text-danger font-bold mt-2 text-center" aria-live="assertive">
          {{ pwdError }}
        </p>

        <div class="flex gap-2 mt-6">
          <button
            type="button"
            class="flex-1 px-5 py-3 bg-subtle text-muted font-bold rounded-[10px] hover:bg-border transition-colors focus:outline-none disabled:opacity-50"
            :disabled="isSubmitting"
            @click="closeModal"
          >
            취소
          </button>
          <button
            type="button"
            class="flex-1 px-5 py-3 bg-primary text-white font-bold rounded-[10px] hover:bg-primary-strong transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-primary-strong"
            :disabled="isSubmitting"
            @click="confirmAction"
          >
            {{ isSubmitting ? '처리 중…' : '확인' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
