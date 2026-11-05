<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MapCanvas from '../components/map/MapCanvas.vue'
import CategoryChips from '../components/explore/CategoryChips.vue'
import PlaceList from '../components/explore/PlaceList.vue'
import BottomSheet from '../components/explore/BottomSheet.vue'
import BasePointControl from '../components/explore/BasePointControl.vue'
import ResearchButton from '../components/explore/ResearchButton.vue'
import { fetchPlace, fetchPlaces } from '../api/places'
import { fetchWeather } from '../api/weather'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useBasePoint } from '../composables/useBasePoint'
import { searchState, toApiParams, toQuery, useExploreQuery } from '../composables/useExploreQuery'
import { useLanternsStore } from '../stores/lanterns'
import { mergeUserMarkers, useMarkersStore } from '../stores/markers'
import { bboxToPoints, demoPosition, haversineMeters, radiusFitPoints } from '../utils/geo'
import { formatRadius } from '../utils/format'

const SHEET_COLLAPSED_PX = 96
const MAP_DARK_KEY = 'jinjuhub.mapDark'

const route = useRoute()
const router = useRouter()
const { isDesktop, isTablet, isMobile } = useBreakpoint()
const { state, update } = useExploreQuery()
const lanterns = useLanternsStore()
const markersStore = useMarkersStore()

const mapRef = ref(null)
const listScroll = ref(null)
const sheetRef = ref(null)
const onExplore = () => route.name === 'explore'
const hasCoords = (p) => !!p && Number.isFinite(p.lat) && Number.isFinite(p.lng)

// Selection: hover (list) and selected (map click / card click).
const hoverId = ref(null)
const selectedId = ref(null)
const activeId = computed(() => hoverId.value || selectedId.value)

// Layout state.
const sheetSnap = ref(state.value.q ? 'half' : 'collapsed')
const panelOpen = ref(true)
const showPanel = computed(() => !isMobile.value && (isDesktop.value || panelOpen.value))
// Map area hidden by the sheet: fits, popups and "이 지역 재검색" bbox use only the visible part.
const viewportH = ref(window.innerHeight)
const onResize = () => {
  viewportH.value = window.innerHeight
}
const insetBottom = computed(() => {
  if (!isMobile.value) return 0
  return sheetSnap.value === 'half' ? Math.round(viewportH.value * 0.5) : SHEET_COLLAPSED_PX
})

// ---------- feedback: toast + screen-reader announcements ----------
const toast = ref('')
const undoPlace = ref(null)
const announcement = ref('')
let toastTimer = null
function showToast(message, undo = null) {
  toast.value = message
  undoPlace.value = undo
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
    undoPlace.value = null
  }, undo ? 4000 : 2400)
}

function undoUnsave() {
  if (undoPlace.value) {
    const item = undoPlace.value
    lanterns.restore(item)
    const title = item.title || '장소'
    undoPlace.value = null
    toast.value = ''
    clearTimeout(toastTimer)
    showToast(`◇ ‘${title}’ 다시 담았어요`)
  }
}

// ---------- list (GET /api/places) ----------
const result = shallowRef({ items: [], total: 0, page: 1, totalPages: 0 })
const listLoading = ref(true)
const listError = ref(false)
const loadedOnce = ref(false)
let requestSeq = 0

const apiParams = computed(() => toApiParams(state.value, { fallbackNear: lanterns.base }))
const apiKey = computed(() => JSON.stringify(apiParams.value))
const searchMode = computed(() => !!state.value.q || state.value.tags.length > 0)
const fitTo = shallowRef(null)

function fitToSearchResults() {
  if (!searchMode.value || state.value.bbox) return
  const points = result.value.items.filter(hasCoords).map((p) => ({ lat: p.lat, lng: p.lng }))
  if (points.length) fitTo.value = points
}

async function loadList() {
  const seq = ++requestSeq
  listLoading.value = true
  listError.value = false
  try {
    const data = await fetchPlaces(apiParams.value)
    if (seq !== requestSeq) return
    result.value = {
      items: Array.isArray(data?.items) ? data.items : [],
      total: data?.total ?? 0,
      page: data?.page ?? 1,
      totalPages: data?.totalPages ?? 0,
    }
    loadedOnce.value = true
    announcement.value = `장소 ${result.value.total.toLocaleString()}곳을 찾았어요.`
    fitToSearchResults()
  } catch {
    if (seq === requestSeq) listError.value = true
  } finally {
    if (seq === requestSeq) listLoading.value = false
  }
}

watch(
  apiKey,
  () => {
    if (!onExplore()) return
    selectedId.value = null
    loadList()
    // New query -> new results: start reading from the top.
    if (listScroll.value) listScroll.value.scrollTop = 0
    sheetRef.value?.scrollToTop()
  },
  { immediate: true },
)

// ---------- markers ----------
// Browsing: every place (clustered), filtered by category chips and the lodging radius.
// Searching (keyword / tag filter): only the current result page, so pins match the list.
// Either way the user's saved/lit places stay visible (separate, unclustered layer).
const filteredMarkers = computed(() => {
  if (searchMode.value) {
    return result.value.items.filter(hasCoords).map((p) => ({
      id: p.id,
      lat: p.lat,
      lng: p.lng,
      category: p.category,
      title: p.title,
      is_collection: p.is_collection,
    }))
  }
  let list = markersStore.byCategory(state.value.categories)
  const { near, radius } = state.value
  if (near && radius) list = list.filter((m) => haversineMeters(near, m) <= radius)
  return list
})
const mapMarkers = computed(() => mergeUserMarkers(filteredMarkers.value, lanterns.items, markersStore.byId))

const savedIds = computed(() => new Set(Object.keys(lanterns.items)))
const litIds = computed(() => new Set(Object.keys(lanterns.items).filter((id) => lanterns.items[id]?.litAt)))

// ---------- lodging / reference point (useBasePoint) ----------
const basePoint = useBasePoint({
  state,
  update,
  onBaseSet: (base) => showToast(`🏠 ‘${base.label}’ 기준으로 볼게요`),
})
const { refPoint, activeRadius, picking, locating, message: baseMessage } = basePoint

function startPicking() {
  basePoint.startPicking()
  mapRef.value?.closePopup()
  if (isMobile.value) sheetSnap.value = 'collapsed'
}

// Marker failures leave an empty map: say so and offer a retry (the list retry does both).
function loadMarkers() {
  return markersStore.load().catch(() => {})
}
function retryAll() {
  if (listError.value || !loadedOnce.value) loadList()
  if (markersStore.error) loadMarkers()
}

function onKeydown(event) {
  if (event.key === 'Escape' && picking.value) basePoint.cancelPicking()
}

// ---------- map viewport: fits and "이 지역 재검색" ----------
const pendingBbox = ref(null)
const showResearch = computed(() => !!pendingBbox.value && pendingBbox.value !== state.value.bbox)

watch(
  () => [state.value.near?.lat, state.value.near?.lng, state.value.radius],
  () => {
    if (!onExplore()) return
    const { near, radius } = state.value
    if (near && radius) fitTo.value = radiusFitPoints(near, radius)
  },
  { immediate: true },
)

function onMoveEnd(bbox) {
  pendingBbox.value = bbox
}

function research() {
  const bbox = pendingBbox.value
  pendingBbox.value = null
  if (bbox) update({ bbox })
}

// ---------- selection: list <-> map ----------
const preview = computed(() => {
  const id = selectedId.value
  if (!id || result.value.items.some((p) => p.id === id)) return null
  return markersStore.byId.get(id) || mapMarkers.value.find((m) => m.id === id) || null
})
const previewDistance = computed(() =>
  preview.value && refPoint.value ? Math.round(haversineMeters(refPoint.value, preview.value)) : null,
)

function onMarkerSelect(id) {
  selectedId.value = id
}

const detailHref = (id) => router.resolve({ name: 'place', params: { id } }).href

function openDetail(id) {
  router.push({ name: 'place', params: { id } })
}

function onCardSelect(id) {
  selectedId.value = id
  if (mapRef.value?.focusMarker(id)) {
    if (isMobile.value) sheetSnap.value = 'collapsed'
    return
  }
  // No pin for it (e.g. a course without coordinates): go straight to the detail page.
  const place = result.value.items.find((p) => p.id === id)
  if (place && !hasCoords(place)) openDetail(id)
}

// ---------- 담기 ----------
function findSummary(id) {
  return result.value.items.find((p) => p.id === id) || markersStore.byId.get(id) || null
}

function toggleSave(placeOrId) {
  const id = typeof placeOrId === 'string' ? placeOrId : placeOrId?.id
  if (!id || lanterns.isLit(id)) return
  if (lanterns.isSaved(id)) {
    const snap = lanterns.items[id] ? { ...lanterns.items[id] } : (findSummary(id) || { id, title: id })
    lanterns.unsave(id)
    showToast('담기를 취소했어요', snap)
    return
  }
  const summary = typeof placeOrId === 'object' ? placeOrId : findSummary(id)
  if (!summary) return
  lanterns.save(summary)
  showToast(`◇ ‘${summary.title}’ 담았어요`)
  // Map markers carry no tags; refresh the snapshot so tag-based badges (e.g. 밤의 남강) work.
  if (!Array.isArray(summary.tags)) {
    fetchPlace(id)
      .then((detail) => {
        if (detail && lanterns.isSaved(id)) lanterns.save({ ...detail, id })
      })
      .catch(() => {})
  }
}

// ---------- filters, sort, search, paging ----------
const searchText = ref(state.value.q)
watch(
  () => state.value.q,
  (q) => {
    if (onExplore()) searchText.value = q
  },
)

function submitSearch() {
  router.push({ name: 'explore', query: toQuery(searchState(state.value, searchText.value)) })
  if (isMobile.value) {
    document.activeElement?.blur?.()
    sheetSnap.value = 'half'
  }
}

function clearSearch() {
  searchText.value = ''
  update({ q: '' })
}

const hasFilters = computed(() => {
  const s = state.value
  return !!(s.q || s.categories.length || s.tags.length || s.bbox || s.radius)
})

function resetFilters() {
  router.push({ name: 'explore', query: toQuery(searchState({ ...state.value, near: null, radius: null }, '')) })
}

// Without a keyword, "추천순" already puts 진주8경 / 유등 30선 first, so the collection option is folded in.
const sortOptions = computed(() =>
  [
    { value: 'relevance', label: state.value.q ? '관련도순' : '추천순' },
    { value: 'distance', label: '가까운순', disabled: !refPoint.value },
    { value: 'name', label: '이름순' },
    state.value.q && { value: 'collection', label: '유등 30선 먼저' },
  ].filter(Boolean),
)
const effectiveSort = computed(() => {
  const sort = apiParams.value.sort
  return sort === 'collection' && !state.value.q ? 'relevance' : sort
})

function setPage(page) {
  update({ page })
}

const countText = computed(() => {
  if (!loadedOnce.value) return '장소 불러오는 중…'
  const n = result.value.total.toLocaleString()
  if (activeRadius.value) return `숙소 ${formatRadius(activeRadius.value)} 안 ${n}곳`
  if (state.value.bbox) return `지도 영역 안 ${n}곳`
  return `장소 ${n}곳`
})
const heading = computed(() => (state.value.q ? `‘${state.value.q}’ 검색 결과` : '진주 탐색'))

// ---------- weather -> "비 오면 실내" highlight ----------
const indoorRecommended = ref(false)

// ---------- demo mode virtual position ----------
const virtualPos = computed(() => demoPosition(lanterns.demo))
function onMoveVirtual(pos) {
  lanterns.setDemo({ ...lanterns.demo, pos })
}

// ---------- night map (per-viewer convenience) ----------
function readMapDark() {
  try {
    return localStorage.getItem(MAP_DARK_KEY) === '1'
  } catch {
    return false
  }
}
const mapDark = ref(readMapDark())
function toggleMapDark() {
  mapDark.value = !mapDark.value
  try {
    localStorage.setItem(MAP_DARK_KEY, mapDark.value ? '1' : '0')
  } catch {
    // Storage unavailable (private mode): keep the in-memory choice.
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
  loadMarkers()
  if (state.value.bbox && !activeRadius.value) fitTo.value = bboxToPoints(state.value.bbox)
  fetchWeather()
    .then((w) => {
      indoorRecommended.value = w?.recommendation === 'indoor'
    })
    .catch(() => {})
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  clearTimeout(toastTimer)
})
</script>

<template>
  <div class="explore relative flex h-full min-h-[420px] overflow-hidden">
    <p class="sr-only" aria-live="polite">{{ announcement }}</p>

    <!-- Desktop / tablet side panel -->
    <aside
      v-if="!isMobile"
      v-show="showPanel"
      class="flex flex-col flex-none bg-surface border-r border-border z-[2]"
      :style="{ width: isDesktop ? '420px' : '360px' }"
      aria-label="장소 목록"
    >
      <div class="flex-none p-4 pb-3 space-y-3 border-b border-border">
        <div class="flex items-end justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-[20px] font-extrabold text-strong truncate">{{ heading }}</h1>
            <p class="text-[13px] font-semibold text-muted">{{ countText }}</p>
          </div>
          <label class="flex-none">
            <span class="sr-only">정렬</span>
            <select class="sort-select" :value="effectiveSort" @change="update({ sort: $event.target.value })">
              <option v-for="o in sortOptions" :key="o.value" :value="o.value" :disabled="o.disabled">
                {{ o.label }}
              </option>
            </select>
          </label>
        </div>

        <div v-if="state.q || state.bbox" class="flex flex-wrap gap-1.5">
          <button v-if="state.q" type="button" class="filter-pill" @click="clearSearch">
            <span class="truncate">검색어: {{ state.q }}</span>
            <span aria-hidden="true">✕</span><span class="sr-only">검색어 지우기</span>
          </button>
          <button v-if="state.bbox" type="button" class="filter-pill" @click="update({ bbox: null })">
            지도 영역으로 제한 <span aria-hidden="true">✕</span><span class="sr-only">영역 제한 해제</span>
          </button>
        </div>

        <CategoryChips
          :categories="state.categories"
          :tags="state.tags"
          :counts="markersStore.counts"
          :indoor-recommended="indoorRecommended"
          @update:categories="update({ categories: $event })"
          @update:tags="update({ tags: $event })"
        />

        <BasePointControl
          :base="refPoint"
          :radius="activeRadius"
          :picking="picking"
          :locating="locating"
          :message="baseMessage"
          @pick="startPicking"
          @cancel-pick="basePoint.cancelPicking"
          @locate="basePoint.locate"
          @update:radius="basePoint.setRadius"
          @clear="basePoint.clearBase"
        />
      </div>

      <div ref="listScroll" class="flex-1 min-h-0 overflow-y-auto">
        <PlaceList
          :items="result.items"
          :loading="listLoading"
          :error="listError"
          :page="result.page"
          :total-pages="result.totalPages"
          :active-id="activeId"
          :selected-id="selectedId"
          :saved-ids="savedIds"
          :lit-ids="litIds"
          :preview="preview"
          :preview-distance="previewDistance"
          :base-point="lanterns.base"
          :has-filters="hasFilters"
          @hover="hoverId = $event"
          @select="onCardSelect"
          @toggle-save="toggleSave"
          @set-base="basePoint.setFromPlace"
          @update:page="setPage"
          @retry="retryAll"
          @reset="resetFilters"
        />
      </div>
    </aside>

    <!-- Map -->
    <div class="relative flex-1 min-w-0">
      <MapCanvas
        ref="mapRef"
        :markers="mapMarkers"
        :saved-ids="savedIds"
        :lit-ids="litIds"
        :active-id="activeId"
        :base="refPoint"
        :radius="activeRadius"
        :fit-to="fitTo"
        :picking-base="picking"
        :virtual-pos="virtualPos"
        :inset-bottom="insetBottom"
        :dark="mapDark"
        :detail-href="detailHref"
        @select="onMarkerSelect"
        @moveend="onMoveEnd"
        @pick-base="basePoint.pickAt"
        @move-virtual="onMoveVirtual"
        @toggle-save="toggleSave"
        @open="openDetail"
      />

      <div
        v-if="markersStore.error"
        data-test="markers-error"
        class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[3] w-[calc(100%-32px)] max-w-[320px] rounded-2xl bg-surface shadow-xl border border-border p-4 text-center"
        role="alert"
      >
        <p class="text-[15px] font-extrabold text-strong">지도에 장소를 표시하지 못했어요.</p>
        <p class="mt-1 text-[13px] text-muted">네트워크 상태를 확인한 뒤 다시 시도해 주세요.</p>
        <button
          type="button"
          class="mt-3 h-9 px-4 rounded-lg bg-night-900 text-white text-[14px] font-bold"
          @click="retryAll"
        >
          다시 시도
        </button>
      </div>

      <!-- Top overlay: chips (mobile), re-search, picking hint -->
      <div class="absolute inset-x-0 top-0 z-[3] pointer-events-none flex flex-col items-center gap-2 p-2 md:p-3">
        <div v-if="isMobile" class="w-full pointer-events-auto">
          <CategoryChips
            :wrap="false"
            :categories="state.categories"
            :tags="state.tags"
            :counts="markersStore.counts"
            :indoor-recommended="indoorRecommended"
            @update:categories="update({ categories: $event })"
            @update:tags="update({ tags: $event })"
          />
        </div>
        <div
          v-if="picking"
          class="pointer-events-auto flex items-center gap-2 rounded-full bg-night-900 text-white text-[13px] font-bold pl-4 pr-1.5 py-1.5 shadow-lg"
          role="status"
        >
          📍 지도를 눌러 숙소 위치를 골라 주세요
          <button type="button" class="rounded-full bg-white/15 hover:bg-white/25 px-3 py-1" @click="basePoint.cancelPicking">
            취소
          </button>
        </div>
        <div v-else class="pointer-events-auto">
          <ResearchButton :visible="showResearch" :loading="listLoading" @click="research" />
        </div>
      </div>

      <!-- Map controls: panel toggle (tablet), night map -->
      <button
        v-if="isTablet"
        type="button"
        class="map-ctrl absolute left-3 top-3 z-[3]"
        :aria-expanded="String(panelOpen)"
        @click="panelOpen = !panelOpen"
      >
        <span aria-hidden="true">{{ panelOpen ? '◀' : '☰' }}</span>
        {{ panelOpen ? '목록 접기' : '목록 보기' }}
      </button>
      <button
        type="button"
        class="map-ctrl absolute right-3 z-[3]"
        :class="isMobile ? 'top-[52px] px-2.5' : 'top-3'"
        :aria-pressed="String(mapDark)"
        :aria-label="mapDark ? '주간 지도로 보기' : '야간 지도로 보기'"
        @click="toggleMapDark"
      >
        <span aria-hidden="true">{{ mapDark ? '☀️' : '🌙' }}</span>
        <span v-if="!isMobile" aria-hidden="true">{{ mapDark ? '주간 지도' : '야간 지도' }}</span>
      </button>

      <!-- Toast -->
      <Transition name="toast">
        <div
          v-if="toast"
          class="toast absolute left-1/2 z-[600] rounded-full bg-night-900 text-white text-[13px] font-bold px-4 py-2 shadow-lg whitespace-nowrap flex items-center gap-2"
          :style="{ bottom: `${insetBottom + 16}px` }"
          role="status"
        >
          <span>{{ toast }}</span>
          <button
            v-if="undoPlace"
            type="button"
            data-test="toast-undo"
            class="text-lantern-500 font-extrabold underline underline-offset-2 ml-1"
            @click="undoUnsave"
          >
            실행 취소
          </button>
        </div>
      </Transition>

      <!-- Mobile bottom sheet -->
      <BottomSheet v-if="isMobile" ref="sheetRef" v-model:snap="sheetSnap" :summary="countText" label="장소 목록">
        <template #header>
          <form role="search" class="relative" @submit.prevent="submitSearch">
            <label for="sheet-search" class="sr-only">장소 검색</label>
            <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-[14px]" aria-hidden="true">🔍</span>
            <input
              id="sheet-search"
              name="search"
              v-model="searchText"
              type="search"
              enterkeyhint="search"
              placeholder="장소, 음식, 축제 검색"
              aria-label="장소 검색"
              class="sheet-search w-full h-10 rounded-full bg-subtle pl-10 pr-10 text-[15px] text-strong outline-none focus:ring-2 focus:ring-lantern-500"
              @focus="sheetSnap === 'collapsed' && (sheetSnap = 'half')"
            />
            <button
              v-if="searchText"
              type="button"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full text-muted hover:bg-border"
              aria-label="검색어 지우기"
              @click="clearSearch"
            >
              ✕
            </button>
          </form>
        </template>

        <div class="px-3 pt-1 pb-2 space-y-2">
          <BasePointControl
            :base="refPoint"
            :radius="activeRadius"
            :picking="picking"
            :locating="locating"
            :message="baseMessage"
            @pick="startPicking"
            @cancel-pick="basePoint.cancelPicking"
            @locate="basePoint.locate"
            @update:radius="basePoint.setRadius"
            @clear="basePoint.clearBase"
          />
          <div class="flex items-center gap-2">
            <button v-if="state.bbox" type="button" class="filter-pill" @click="update({ bbox: null })">
              지도 영역 <span aria-hidden="true">✕</span><span class="sr-only">영역 제한 해제</span>
            </button>
            <label class="ml-auto">
              <span class="sr-only">정렬</span>
              <select class="sort-select" :value="effectiveSort" @change="update({ sort: $event.target.value })">
                <option v-for="o in sortOptions" :key="o.value" :value="o.value" :disabled="o.disabled">
                  {{ o.label }}
                </option>
              </select>
            </label>
          </div>
        </div>

        <PlaceList
          :items="result.items"
          :loading="listLoading"
          :error="listError"
          :page="result.page"
          :total-pages="result.totalPages"
          :active-id="activeId"
          :selected-id="selectedId"
          :saved-ids="savedIds"
          :lit-ids="litIds"
          :preview="preview"
          :preview-distance="previewDistance"
          :base-point="lanterns.base"
          :has-filters="hasFilters"
          @select="onCardSelect"
          @toggle-save="toggleSave"
          @set-base="basePoint.setFromPlace"
          @update:page="setPage"
          @retry="retryAll"
          @reset="resetFilters"
        />
      </BottomSheet>
    </div>
  </div>
</template>

<style scoped>
.sort-select {
  height: 34px;
  padding: 0 28px 0 10px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2364748b' stroke-width='1.6' fill='none'/%3E%3C/svg%3E")
    no-repeat right 10px center;
  appearance: none;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-body);
}
.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--primary-tint);
  border: 1px solid var(--selected-border);
  color: var(--color-night-700);
  font-size: 12px;
  font-weight: 700;
  max-width: 100%;
}
.map-ctrl {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-night-900);
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 2px 8px rgb(15 27 61 / 0.2);
}
.map-ctrl:hover {
  background: #f8fafc;
}
.toast {
  transform: translateX(-50%);
}
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}
.sheet-search::-webkit-search-cancel-button {
  display: none;
}
@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}
</style>
