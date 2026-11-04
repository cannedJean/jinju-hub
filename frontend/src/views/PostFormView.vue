<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StateView from '../components/StateView.vue'
import { fetchPost, createPost, updatePost } from '../api/posts'
import { getApiDetail, getApiStatus, getValidationErrors } from '../api/client'
import { usePostAuthStore } from '../stores/postAuth'
import { POST_CATEGORIES } from '../utils/constants'

const route = useRoute()
const router = useRouter()
const authStore = usePostAuthStore()

const categories = POST_CATEGORIES
const isEdit = computed(() => route.name === 'post-edit')

const form = reactive({ category: '', title: '', content: '', password: '' })
const fieldErrors = reactive({ category: '', title: '', content: '', password: '' })
const generalError = ref('')

const loading = ref(false)
const error = ref(false)
const errorMessage = ref('')
const isSubmitting = ref(false)

async function loadData() {
  if (!isEdit.value) return
  loading.value = true
  error.value = false
  try {
    const data = await fetchPost(route.params.id)
    form.category = data.category
    form.title = data.title
    form.content = data.content
    // Password entered in the detail modal (may be empty if the user navigated here directly).
    form.password = authStore.take(route.params.id)
  } catch (e) {
    error.value = true
    errorMessage.value =
      getApiStatus(e) === 404 ? '존재하지 않는 게시글입니다.' : '게시글을 불러올 수 없습니다.'
  } finally {
    loading.value = false
  }
}

function resetErrors() {
  fieldErrors.category = ''
  fieldErrors.title = ''
  fieldErrors.content = ''
  fieldErrors.password = ''
  generalError.value = ''
}

function validate() {
  let valid = true
  if (!form.category) {
    fieldErrors.category = '카테고리를 선택해 주세요.'
    valid = false
  }
  if (!form.title.trim()) {
    fieldErrors.title = '제목을 입력해 주세요.'
    valid = false
  }
  if (!form.content.trim()) {
    fieldErrors.content = '내용을 입력해 주세요.'
    valid = false
  }
  if (!form.password || form.password.length < 4) {
    fieldErrors.password = '비밀번호를 4자 이상 입력해 주세요.'
    valid = false
  }
  return valid
}

async function submit() {
  resetErrors()
  if (!validate()) return

  isSubmitting.value = true
  const payload = {
    category: form.category,
    title: form.title.trim(),
    content: form.content.trim(),
    password: form.password,
  }

  try {
    if (isEdit.value) {
      await updatePost(route.params.id, payload)
      router.push(`/boards/${route.params.id}`)
    } else {
      const created = await createPost(payload)
      router.push(created?.id !== undefined ? `/boards/${created.id}` : '/boards')
    }
  } catch (e) {
    const status = getApiStatus(e)
    if (status === 422) {
      Object.assign(fieldErrors, getValidationErrors(e))
      if (!Object.values(fieldErrors).some(Boolean)) {
        generalError.value = '입력값을 다시 확인해 주세요.'
      }
    } else if (status === 403 && isEdit.value) {
      fieldErrors.password = '비밀번호가 일치하지 않습니다.'
    } else {
      generalError.value = getApiDetail(e, '작업 중 오류가 발생했습니다.')
    }
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="max-w-[800px] mx-auto px-6 py-8 min-h-[calc(100vh-260px)]">
    <h1 class="text-[26px] font-extrabold text-heading mb-6">{{ isEdit ? '글 수정' : '새 글 쓰기' }}</h1>

    <StateView
      v-if="isEdit && (loading || error)"
      :loading="loading"
      :error="error"
      :error-message="errorMessage"
      @retry="loadData"
    />

    <div v-else class="bg-white rounded-[14px] border border-border shadow-sm p-6 md:p-10">
      <form class="flex flex-col gap-6" @submit.prevent="submit">
        <div>
          <label for="f-category" class="block text-[14px] font-bold text-strong mb-2">카테고리 *</label>
          <select
            id="f-category"
            v-model="form.category"
            class="w-full h-[46px] bg-page border border-border-input rounded-[10px] px-4 outline-none text-[15px] focus:border-primary focus:ring-1 focus:ring-primary"
            :class="{ '!border-danger': fieldErrors.category }"
          >
            <option value="" disabled>카테고리를 선택하세요</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.label }}</option>
          </select>
          <p v-if="fieldErrors.category" class="text-[13px] text-danger font-bold mt-1" aria-live="assertive">
            {{ fieldErrors.category }}
          </p>
        </div>

        <div>
          <label for="f-title" class="block text-[14px] font-bold text-strong mb-2">제목 *</label>
          <input
            id="f-title"
            v-model="form.title"
            type="text"
            maxlength="100"
            placeholder="제목을 입력하세요 (최대 100자)"
            class="w-full h-[46px] bg-page border border-border-input rounded-[10px] px-4 outline-none text-[15px] focus:border-primary focus:ring-1 focus:ring-primary"
            :class="{ '!border-danger': fieldErrors.title }"
          />
          <p v-if="fieldErrors.title" class="text-[13px] text-danger font-bold mt-1" aria-live="assertive">
            {{ fieldErrors.title }}
          </p>
        </div>

        <div>
          <label for="f-content" class="block text-[14px] font-bold text-strong mb-2">내용 *</label>
          <textarea
            id="f-content"
            v-model="form.content"
            placeholder="지역 주민들과 나누고 싶은 이야기를 자유롭게 적어주세요."
            class="w-full min-h-[160px] bg-page border border-border-input rounded-[10px] p-4 outline-none text-[15px] resize-y focus:border-primary focus:ring-1 focus:ring-primary"
            :class="{ '!border-danger': fieldErrors.content }"
          ></textarea>
          <p v-if="fieldErrors.content" class="text-[13px] text-danger font-bold mt-1" aria-live="assertive">
            {{ fieldErrors.content }}
          </p>
        </div>

        <div>
          <label for="f-pwd" class="block text-[14px] font-bold text-strong mb-2">비밀번호 *</label>
          <input
            id="f-pwd"
            v-model="form.password"
            type="password"
            minlength="4"
            placeholder="••••••"
            class="w-full h-[46px] bg-page border border-border-input rounded-[10px] px-4 outline-none text-[15px] mb-2 focus:border-primary focus:ring-1 focus:ring-primary"
            :class="{ '!border-danger': fieldErrors.password }"
          />
          <p class="text-[12px] font-semibold" style="color: var(--cat-food)">
            ⚠ 수정·삭제 시 필요합니다. 4자 이상 입력해 주세요.
          </p>
          <p v-if="fieldErrors.password" class="text-[13px] text-danger font-bold mt-1" aria-live="assertive">
            {{ fieldErrors.password }}
          </p>
        </div>

        <div v-if="generalError" class="p-3 bg-danger-bg border border-danger-border rounded-lg">
          <p class="text-[14px] text-danger font-bold text-center" aria-live="assertive">{{ generalError }}</p>
        </div>

        <div class="flex justify-end gap-3 mt-2 pt-4 border-t border-border">
          <button
            type="button"
            class="px-6 py-3 border border-border-input text-muted font-bold rounded-[10px] hover:bg-page transition-colors focus:outline-none"
            @click="router.back()"
          >
            취소
          </button>
          <button
            type="submit"
            class="px-8 py-3 bg-primary text-white font-bold rounded-[10px] hover:bg-primary-strong transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-primary-strong"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? '처리 중…' : isEdit ? '수정 완료' : '등록' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
