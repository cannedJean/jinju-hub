<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StateView from '../components/StateView.vue'
import Pagination from '../components/Pagination.vue'
import { fetchPosts } from '../api/posts'
import { normalizePage } from '../utils/normalizers'
import { POST_CATEGORIES, getCategoryColor, getCategoryLabel, formatDateShort } from '../utils/constants'

const route = useRoute()
const router = useRouter()

const categories = POST_CATEGORIES

const filterCat = ref(route.query.category || null)
const filterKeyword = ref(route.query.keyword || '')
const parsePage = (value) => Math.max(1, Number.parseInt(value, 10) || 1)
const page = ref(parsePage(route.query.page))

const posts = ref([])
const totalPages = ref(1)
const loading = ref(true)
const error = ref(false)

async function loadData() {
  loading.value = true
  error.value = false
  try {
    const params = { page: page.value, size: 10 }
    if (filterCat.value) params.category = filterCat.value
    if (filterKeyword.value) params.keyword = filterKeyword.value

    const data = await fetchPosts(params)
    const normalized = normalizePage(data)
    posts.value = normalized.items
    totalPages.value = normalized.totalPages
  } catch {
    error.value = true
    posts.value = []
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  const query = {}
  if (filterCat.value) query.category = filterCat.value
  if (filterKeyword.value) query.keyword = filterKeyword.value
  if (page.value > 1) query.page = page.value
  router.push({ path: '/boards', query })
}

function submitSearch() {
  page.value = 1
  applyFilters()
}

function setCategory(id) {
  filterCat.value = id
  page.value = 1
  applyFilters()
}

function changePage(p) {
  page.value = p
  applyFilters()
}

watch(
  () => route.query,
  (q) => {
    filterCat.value = q.category || null
    filterKeyword.value = q.keyword || ''
    page.value = parsePage(q.page)
    loadData()
  },
)

onMounted(loadData)
</script>

<template>
  <div class="max-w-[1200px] mx-auto px-6 py-8 min-h-[calc(100vh-260px)]">
    <div class="flex flex-col md:flex-row md:justify-between md:items-center mb-8 gap-4">
      <h1 class="text-[26px] font-extrabold text-heading">커뮤니티 게시판</h1>
      <router-link
        to="/boards/new"
        class="bg-primary hover:bg-primary-strong transition-colors text-white px-5 py-2.5 rounded-[10px] font-bold text-[15px] shadow-sm text-center focus:outline-none focus:ring-2 focus:ring-primary"
      >
        ✏️ 글쓰기
      </router-link>
    </div>

    <div class="flex flex-col md:flex-row justify-between mb-4 gap-4">
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="border px-4 py-1.5 rounded-[18px] text-[14px] font-bold transition-colors shadow-sm focus:outline-none"
          :class="!filterCat ? 'bg-primary text-white border-primary' : 'bg-white text-nav border-border-input'"
          @click="setCategory(null)"
        >
          전체
        </button>
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          class="border px-4 py-1.5 rounded-[18px] text-[14px] font-bold transition-colors shadow-sm focus:outline-none"
          :class="filterCat === c.id ? 'bg-primary text-white border-primary' : 'bg-white text-nav border-border-input'"
          @click="setCategory(c.id)"
        >
          {{ c.label }}
        </button>
      </div>
      <div class="relative w-full md:w-64">
        <label for="board-search" class="sr-only">게시글 검색</label>
        <input
          id="board-search"
          v-model="filterKeyword"
          type="text"
          placeholder="🔍 제목·내용 검색"
          class="w-full bg-white border border-border-input rounded-[10px] pl-4 pr-4 py-2 outline-none text-[14px] focus:border-primary focus:ring-1 focus:ring-primary"
          @keyup.enter="submitSearch"
        />
      </div>
    </div>

    <div class="bg-white rounded-[14px] border border-border overflow-hidden shadow-sm">
      <div
        class="hidden md:grid grid-cols-[80px_120px_1fr_120px_80px] bg-subtle py-3.5 px-4 border-b border-border text-[13px] font-bold text-muted text-center"
      >
        <div>번호</div>
        <div>카테고리</div>
        <div class="text-left px-4">제목</div>
        <div>작성일</div>
        <div>조회</div>
      </div>

      <StateView
        :loading="loading"
        :error="error"
        :empty="posts.length === 0"
        empty-message="검색 결과가 없습니다."
        @retry="loadData"
      >
        <div class="flex flex-col">
          <button
            v-for="p in posts"
            :key="p.id"
            type="button"
            class="border-b border-border-list hover:bg-page transition-colors last:border-0 w-full text-left focus:outline-none focus:bg-page"
            @click="router.push(`/boards/${p.id}`)"
          >
            <div class="grid md:grid-cols-[80px_120px_1fr_120px_80px] px-4 py-4 items-center gap-2 md:gap-0 md:h-[60px]">
              <div class="hidden md:block text-center text-muted text-[14px] font-medium">{{ p.id }}</div>
              <div class="text-left md:text-center shrink-0">
                <span :class="['cat-badge', getCategoryColor(p.category)]">
                  {{ getCategoryLabel(p.category) }}
                </span>
              </div>
              <div class="text-[15px] font-medium text-strong truncate md:px-4">{{ p.title }}</div>
              <div class="text-left md:text-center text-[13px] text-faint font-medium shrink-0">
                {{ formatDateShort(p.created_at) }}
              </div>
              <div class="hidden md:block text-center text-[13px] text-muted font-medium">
                {{ p.views !== undefined && p.views !== null ? p.views : '-' }}
              </div>
            </div>
          </button>
        </div>
      </StateView>
    </div>

    <Pagination :page="page" :total-pages="totalPages" @update:page="changePage" />
  </div>
</template>
